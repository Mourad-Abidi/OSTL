# gui.py
import tkinter as tk
from tkinter import ttk, scrolledtext
from bot import Bot

class App:
    def __init__(self, root, bot):
        self.root = root; self.bot = bot
        root.title("One-Shot Concept Learner")
        root.geometry("1200x720")

        paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left: chat
        left = ttk.Frame(paned); paned.add(left, weight=2)
        self.chat = scrolledtext.ScrolledText(left, wrap=tk.WORD, state=tk.DISABLED,
                                             font=("Menlo", 11))
        self.chat.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        bar = ttk.Frame(left); bar.pack(fill=tk.X, padx=5, pady=5)
        self.entry = ttk.Entry(bar, font=("Menlo", 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self.send)
        ttk.Button(bar, text="Send", command=self.send).pack(side=tk.RIGHT, padx=(4,0))

        # Right: concept graph
        right = ttk.Frame(paned); paned.add(right, weight=1)
        ttk.Label(right, text="Concept graph",
                  font=("TkDefaultFont", 12, "bold")).pack(pady=(8,0))
        self.canvas = tk.Canvas(right, bg="#fafafa", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Configure>", lambda e: self.draw())

        self.say("Bot", "Ready. 'help' for commands, or try:\n"
                        '  teach "hello" -> "OLLEH"')

    def say(self, who, text):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, f"{who}: {text}\n\n")
        self.chat.see(tk.END)
        self.chat.config(state=tk.DISABLED)

    def send(self, _=None):
        text = self.entry.get().strip()
        if not text: return
        self.entry.delete(0, tk.END)
        self.say("You", text)
        reply = self.bot.handle(text)
        if reply == "__EXIT__":
            self.root.destroy(); return
        self.say("Bot", reply)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        nodes = self.bot.graph.nodes
        if not nodes: return

        # Layout: layers by graph depth, base concepts at the bottom
        layers = {}
        for name in nodes:
            layers.setdefault(self.bot.graph.depth(name), []).append(name)
        max_d = max(layers) if layers else 0
        W = self.canvas.winfo_width() or 400
        H = self.canvas.winfo_height() or 600
        pos = {}
        for d, names in layers.items():
            y = H * (1 - (d + 1) / (max_d + 2))
            for i, n in enumerate(names):
                x = W * (i + 1) / (len(names) + 1)
                pos[n] = (x, y)

        # Edges
        for name, n in nodes.items():
            for dep in n.dependencies:
                if dep in pos:
                    x1, y1 = pos[dep]; x2, y2 = pos[name]
                    self.canvas.create_line(x1, y1, x2, y2,
                                            arrow=tk.LAST, fill="#aaa", width=1.5)

        # Nodes
        R = 22
        for name, (x, y) in pos.items():
            is_abs = name.startswith("abstract")
            is_base = name.startswith("concept")
            color = "#7a4ad9" if is_abs else ("#4a90d9" if is_base else "#888")
            self.canvas.create_oval(x-R, y-R, x+R, y+R,
                                    fill=color, outline="#333", width=1.5)
            self.canvas.create_text(x, y, text=name, fill="white",
                                    font=("TkDefaultFont", 8, "bold"))

def main():
    root = tk.Tk()
    App(root, Bot(max_size=4))
    root.mainloop()

if __name__ == "__main__":
    main()