# -*- coding: utf-8 -*-
"""
Created on Fri Oct 13 19:57:00 2017

@author: Tsvika
"""
import argparse
from game import EndMode, run_game_n_times, run_game_once
import players


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('player_name')
    parser.add_argument('-t', '--times', default=1, type=int)
    parser.add_argument('-n', '--players', default=3, type=int)
    parser.add_argument('-c', '--allow-cheats', default=False, action='store_true')
    parser.add_argument('-e', '--end-mode', default='official', choices=[e.name for e in EndMode])
    parser.add_argument('-s', '--suits', default=5, type=int)

    args = parser.parse_args()
    player = getattr(players, args.player_name)
    h_args = (args.players, EndMode[args.end_mode], args.suits, args.allow_cheats)
    if args.times > 1:
        scores = run_game_n_times(player, args.times, *h_args)
    if args.times == 1:
        h = run_game_once(player, *h_args)
