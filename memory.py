# memory.py
class ConceptMemory:
    def __init__(self):
        self.concepts = {}   # name -> (program, input_types, ret_type)
        self.counter  = 0

    def next_name(self):
        self.counter += 1
        return f"concept_{self.counter}"

    def add(self, name, program, input_types, ret_type):
        self.concepts[name] = (program, input_types, ret_type)

    def get(self, name):
        return self.concepts.get(name)

    def names(self):
        return list(self.concepts.keys())