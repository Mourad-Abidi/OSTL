# train_neural.py
from neural import train_oracle
oracle = train_oracle(max_size=2, samples_per_program=20, epochs=25)
if oracle:
    oracle.save("neural_oracle.pt")
    print("Saved neural_oracle.pt")