from __future__ import annotations

from collections.abc import Sequence

from .model import MarginModel


def simulate_playin(seeds_1_to_10: Sequence[str], model: MarginModel) -> dict[str, object]:
    """Simulate one conference play-in bracket and return playoff/eliminated teams."""
    if len(seeds_1_to_10) != 10:
        raise ValueError("seeds_1_to_10 must contain exactly 10 teams")
    if len(set(seeds_1_to_10)) != 10:
        raise ValueError("seeds_1_to_10 must not contain duplicate teams")

    seeds = list(seeds_1_to_10)
    seed7, seed8, seed9, seed10 = seeds[6], seeds[7], seeds[8], seeds[9]

    # Game A: 7 hosts 8
    game_a_winner, _ = model.simulate_game(seed7, seed8)
    game_a_loser = seed8 if game_a_winner == seed7 else seed7

    # Game B: 9 hosts 10
    game_b_winner, _ = model.simulate_game(seed9, seed10)
    game_b_loser = seed10 if game_b_winner == seed9 else seed9

    # Final: loser(A) hosts winner(B)
    final_winner, _ = model.simulate_game(game_a_loser, game_b_winner)
    final_loser = game_b_winner if final_winner == game_a_loser else game_a_loser

    playoff_seeds = seeds[:6] + [game_a_winner, final_winner]
    play_in_eliminated = [game_b_loser, final_loser]

    return {
        "playoff_seeds": playoff_seeds,
        "play_in_eliminated": play_in_eliminated,
        "game_a_winner": game_a_winner,
        "game_b_winner": game_b_winner,
        "final_winner": final_winner,
    }
