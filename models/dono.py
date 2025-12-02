class Dono:
    def __init__(self, id, nome, telefone):
        self.id = id
        self.nome = nome
        self.telefone = telefone

    def __repr__(self):
        return f"<Dono {self.nome}>"
