import pandas as pd
import chess
import chess.pgn
import chess.engine
from typing import Dict, Any, Optional
from chesscom.pgnParsing import parse_pgn



class MergedRepertoireNode:
    """A single position in the opening tree holding User, GM, and Engine data."""
    def __init__(self, move_san: str):
        self.move_san: str = move_san
        
        self.user_count: int = 0
        self.user_wins: int = 0
        self.user_losses: int = 0
        self.user_draws: int = 0
        
        self.gm_count: int = 0
        
        self.engine_eval: Optional[float] = None
        self.engine_best_move: Optional[str] = None
        
        self.children: Dict[str, 'MergedRepertoireNode'] = {}

    def add_user_result(self, result: str) -> None:
        self.user_count += 1
        if result == "win":
            self.user_wins += 1
        elif result == "loss":
            self.user_losses += 1
        elif result == "draw":
            self.user_draws += 1

    def add_gm_result(self) -> None:
        self.gm_count += 1

    def to_dict(self) -> Dict[str, Any]:
        score_rate = None
        if self.user_count > 0:
            score_rate = round(
                100.0 * (self.user_wins + 0.5 * self.user_draws) / self.user_count,
                1,
            )

        return {
            "move": self.move_san,
            "count": self.user_count,
            "wins": self.user_wins,
            "draws": self.user_draws,
            "losses": self.user_losses,
            "score_rate": score_rate,
            "gm_count": self.gm_count,
            "children": {k: v.to_dict() for k, v in self.children.items()},
    }

class HumanFirstRepertoireBuilder:
    def __init__(self, target_color: str, depth_limit: int = 15):
        self.target_color: str = target_color.lower()
        self.depth_limit: int = depth_limit
        self.root: MergedRepertoireNode = MergedRepertoireNode("root")

    def build_user_pass(self, user_df: pd.DataFrame, target_opening: str) -> None:
        """PASS 1: Parse user games to build the base tree."""
        target_norm = str(target_opening).strip().lower()

        opening_name_norm = user_df["opening_name"].astype(str).str.strip().str.lower()
        opening_family_norm = user_df["opening_family"].astype(str).str.strip().str.lower()
        color_norm = user_df["my_color"].astype(str).str.strip().str.lower()

        filtered_df = user_df[
            (color_norm == self.target_color)
            & (
                (opening_name_norm == target_norm)
                | (opening_family_norm == target_norm)
            )
        ].copy()
        
        for _, row in filtered_df.iterrows():
            pgn_col = next((col for col in ["pgn", "moves", "Moves"] if col in row.index), None)
            if not pgn_col: continue
                
            game = parse_pgn(str(row[pgn_col]))
            if not game: continue
                
            my_result = str(row.get("simple_result", "Draw"))
            current_node = self.root
            current_node.add_user_result(my_result)
            
            board = game.board()
            for ply, move in enumerate(game.mainline_moves()):
                if ply >= self.depth_limit * 2: break
                
                san_move = board.san(move)
                if san_move not in current_node.children:
                    current_node.children[san_move] = MergedRepertoireNode(san_move)
                
                current_node = current_node.children[san_move]
                current_node.add_user_result(my_result)
                board.push(move)

    def get_mainline_fingerprint(self, ply_depth: int = 4) -> str:
        """Extracts the most common opening sequence to use as a database search string."""
        curr = self.root
        moves = []
        for _ in range(ply_depth):
            if not curr.children: break
            # Find the most commonly played continuation
            best_child = max(curr.children.values(), key=lambda c: c.user_count)
            if best_child.user_count == 0: break
            moves.append(best_child.move_san)
            curr = best_child
        return " ".join(moves)

    def build_gm_pass(self, twic_df: pd.DataFrame) -> None:
        """PASS 2: Overlay TWIC GM games onto the tree."""
        if twic_df.empty: return
        
        for _, row in twic_df.iterrows():
            moves_str = str(row.get("Moves", ""))
            if not moves_str: continue
            
            game = parse_pgn(moves_str)
            if not game: continue
            
            current_node = self.root
            current_node.add_gm_result()
            
            board = game.board()
            for ply, move in enumerate(game.mainline_moves()):
                if ply >= self.depth_limit * 2: break
                
                san_move = board.san(move)
                if san_move not in current_node.children:
                    current_node.children[san_move] = MergedRepertoireNode(san_move)
                
                current_node = current_node.children[san_move]
                current_node.add_gm_result()
                board.push(move)

    def export_to_lichess_study(
        self,
        target_opening: str,
        engine_path: str = "/usr/local/bin/stockfish",
        engine_time: float = 0.10,
        engine_min_delta_cp: int = 50,) -> str:

        """PASS 3: Engine Evaluation & Smart Comment Formatting"""
        game = chess.pgn.Game()
        game.headers["Event"] = f"Human-First Repertoire: {target_opening}"
        game.headers["Site"] = "Chess Analytics Dashboard"

        engine = None
        try:
            engine = chess.engine.SimpleEngine.popen_uci(engine_path)
            engine.configure({"Threads": 2, "Hash": 256})
        except Exception as exc:
            game.headers["Annotator"] = f"Stockfish unavailable: {exc}"

        target_turn = chess.WHITE if self.target_color == "white" else chess.BLACK

        def score_cp(info: chess.engine.InfoDict, pov_color: chess.Color) -> Optional[int]:
            score = info.get("score")
            if score is None:
                return None
            return score.pov(pov_color).score(mate_score=100000)

        def maybe_add_engine_variation(
            tree_node: MergedRepertoireNode,
            child: MergedRepertoireNode,
            pgn_node: chess.pgn.GameNode,
            board: chess.Board,
            actual_move: chess.Move,
            win_rate: float,
        ) -> bool:
            if engine is None:
                return False

            # Only annotate candidate improvements for the user's repertoire side.
            if board.turn != target_turn:
                return False

            # Keep engine noise low.
            if child.user_count < 3:
                return False
            if child.gm_count > 0 and win_rate >= 50:
                return False

            try:
                best_info = engine.analyse(board, chess.engine.Limit(time=engine_time))
                best_move = best_info.get("pv", [None])[0]
                if best_move is None or best_move == actual_move:
                    return False

                best_san = board.san(best_move)

                # Do not duplicate a move that already exists as a user/GM branch.
                if best_san in tree_node.children:
                    return False

                mover = board.turn
                best_eval = score_cp(best_info, mover)
                if best_eval is None:
                    return False

                board.push(actual_move)
                try:
                    actual_info = engine.analyse(board, chess.engine.Limit(time=engine_time))
                    actual_eval = score_cp(actual_info, mover)
                finally:
                    board.pop()

                if actual_eval is None:
                    return False

                delta = best_eval - actual_eval
                if delta < engine_min_delta_cp:
                    return False

                engine_var = pgn_node.add_variation(best_move)
                engine_var.comment = (
                    f"🤖 Stockfish Improvement: {best_san} "
                    f"({best_eval / 100.0:+.2f}, improves by {delta} cp)"
                )
                return True

            except Exception:
                return False

        def traverse(node: MergedRepertoireNode, pgn_node: chess.pgn.GameNode, board: chess.Board):
            if not node.children:
                return

            sorted_children = sorted(
                node.children.values(),
                key=lambda x: (x.user_count, x.gm_count),
                reverse=True,
            )
            parent_choices = len([c for c in node.children.values() if c.user_count > 0])
            engine_added_at_position = False

            for i, child in enumerate(sorted_children):
                if child.user_count == 0 and child.gm_count == 0:
                    continue

                try:
                    move = board.parse_san(child.move_san)
                except ValueError:
                    continue

                win_rate = (child.user_wins / child.user_count) * 100 if child.user_count > 0 else 0

                if not engine_added_at_position:
                    engine_added_at_position = maybe_add_engine_variation(
                        node,
                        child,
                        pgn_node,
                        board,
                        move,
                        win_rate,
                    )

                next_pgn = pgn_node.add_main_variation(move) if i == 0 else pgn_node.add_variation(move)

                comments = []
                is_user_deviation = child.user_count > 0 and child.gm_count == 0
                is_leaf = not child.children
                has_siblings = parent_choices > 1

                if child.gm_count > 0 and child.user_count > 0:
                    if has_siblings or is_leaf:
                        icon = "🟢" if win_rate >= 55 else ("🔴" if win_rate <= 45 else "⚪")
                        comments.append(
                            f"{icon} Played {child.user_count}x ({win_rate:.0f}%)"
                            f" | ♔ GM Book {child.gm_count}x"
                        )

                elif is_user_deviation:
                    icon = "🟢" if win_rate >= 55 else ("🔴" if win_rate <= 45 else "⚪")
                    comments.append(
                        f"{icon} Played {child.user_count}x ({win_rate:.0f}%)"
                        " | ⚠️ Out of GM Book"
                    )

                elif child.gm_count > 0 and child.user_count == 0:
                    comments.append(f"♔ GM Move ({child.gm_count}x)")

                if comments:
                    next_pgn.comment = " | ".join(comments)

                board.push(move)
                traverse(child, next_pgn, board)
                board.pop()

        try:
            traverse(self.root, game, chess.Board())
        finally:
            if engine is not None:
                engine.quit()

        return str(game)