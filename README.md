# Tactitalyser

A simple python wrapper around SF to detect brilliant moves, accepts games in pgn format and saves brilliant games in games/out.pgn

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [TODO](#TODO)

## Installation

modify main.py to look for Stockfish executables in the right path and use your desired name in the "name" variable. 
place your input games in the directory ../Tactitalyser/games

## TODO

Handle discovered attacks not to be classified as brilliancies (eg: pushing a pawn where it can be taken for free except that creates a discovery attack on the opponent's queen)

