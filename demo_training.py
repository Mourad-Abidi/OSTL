# demo_training.py
import os
from bot import Bot
from neural import NeuralOracle, train_oracle

oracle = None
if os.path.exists("neural_oracle.pt"):
    oracle = NeuralOracle.load("neural_oracle.pt")
    print("Loaded neural_oracle.pt")
else:
    print("Training a fresh neural oracle…")
    oracle = train_oracle(max_size=2, samples_per_program=20, epochs=25)
    if oracle:
        oracle.save("neural_oracle.pt")
        print("Saved neural_oracle.pt")

bot = Bot(max_size=4, neural_oracle=oracle, neural_online=True)

session = [
    'teach 3 -> 9',
    'teach 5 -> 25',
    'teach 2 -> 4',
    'teach "abc" -> "CBA"',
    'teach "hello" -> "OLLEH"',
    'teach "WORLD" -> "DLROW"',
    'teach 4 -> 16',
    'invent',
    'concepts',
]

for cmd in session:
    print(f"\n>>> {cmd}")
    print(bot.handle(cmd))