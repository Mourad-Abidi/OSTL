# demo.py
from chat import ChatBot

def run():
    bot = ChatBot(max_program_size=4)
    script = [
        'teach "hello" -> "OLLEH"',
        'apply concept_1 "world"',
        'teach "abc" -> "CBA"',           # should reuse concept_1!
        'explain concept_2',
        'concepts',
        'teach 3 -> 9',
        'apply concept_3 7',
    ]
    for line in script:
        print("You:", line)
        print("Bot:", bot.handle(line))
        print()

if __name__ == "__main__":
    run()