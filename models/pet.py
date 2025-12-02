class Pet:
    def __init__(self, id, nome, especie, idade, dono_id):
        self.id = id
        self.nome = nome
        self.especie = especie
        self.idade = idade
        self.dono_id = dono_id

    def __repr__(self):
        return f"<Pet {self.nome} ({self.especie})>"
