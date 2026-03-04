def save_leagues(white, black):
    with open("leagues.txt", "w") as f:
        f.write(",".join(white) + "|" + ",".join(black))

def load_leagues():
    if os.path.exists("leagues.txt"):
        with open("leagues.txt", "r") as f:
            data = f.read().split("|")
            white = set(data[0].split(",")) if data[0] else {"NHL", "KHL", "SHL"}
            black = set(data[1].split(",")) if len(data) > 1 and data[1] else set()
            return white, black
    return {"NHL", "KHL", "SHL"}, set()

# В начале main() используй:
# WHITE_LIST, BLACK_LIST = load_leagues()
# А после добавления новой лиги вызывай save_leagues(WHITE_LIST, BLACK_LIST)
