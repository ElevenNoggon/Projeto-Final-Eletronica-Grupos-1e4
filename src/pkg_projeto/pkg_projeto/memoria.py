#Aquivo para armazenar as figuras encontradas e ordenar os sons.
 
#A memória é indexada pela forma: várias detecções da mesma figura
# figura, vistas em frames e faixas diferentes, votam na cor, logo, 
# a resposta definitiva é aceita quando for confirmada por mais de um teste.
#-------------------------------------------------------------------------#


import math
from collections import Counter

FORMAS = ('circulo', 'hexagono', 'triangulo')

NOMES_COR = ('azul', 'verde', 'vermelho')

def ler_hex(valor):
    if not isinstance(valor, str):      
        return None
    valor = valor.strip().lstrip('#')   
    if len(valor) != 6:                 
        return None
    try:
        n = int(valor, 16)              
    except ValueError:                  
        return None
    return (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF


def _numero(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor))


class Memoria:
    def __init__(self, min_testes=5, min_proporcao=0.7):
        self.min_testes = min_testes
        self.min_proporcao = min_proporcao
        self.testes = {forma: Counter() for forma in FORMAS}
        self._pos = {forma: [0.0, 0.0, 0] for forma in FORMAS}
        self._rgb = {forma: {} for forma in FORMAS} 

    #Registro de detecção
    def registrar(self, forma, cor,cor_hex= None, x=None, y=None):

        rgb = ler_hex(cor_hex)
        
        if forma not in self.testes or cor not in NOMES_COR or rgb is None:
            return False
        
        self.testes[forma][cor] += 1

        acc = self._rgb[forma].setdefault(cor, [0, 0, 0, 0])
        acc[0] += rgb[0]
        acc[1] += rgb[1]
        acc[2] += rgb[2]
        acc[3] += 1

        if _numero(x) and _numero(y):
            acc = self._pos[forma]
            acc[0] += x
            acc[1] += y
            acc[2] += 1
        
        return True


    #Retorna {forma: (cor, votos)} das figuras com cor confirmada
    def confirmados(self, min_testes=None, min_proporcao=None):
        mt = self.min_testes if min_testes is None else min_testes
        mp = self.min_proporcao if min_proporcao is None else min_proporcao
        saida = {}
        for forma, contagem in self.testes.items():
            total = sum(contagem.values())
            if not total:
                continue
            cor, votos = contagem.most_common(1)[0]
            if votos >= mt and votos / total >= mp:
                saida[forma] = (cor, votos)
        return saida


    def completo(self):
        return len(self.confirmados()) == len(FORMAS)


    #Posição média (x,y) da figura no frame local
    def posicao(self, forma):
        sx, sy, n = self._pos[forma]
        return (sx / n, sy / n) if n else None

    def valor_hex(self, forma, cor=None):
        if cor is None:
            if not self.testes[forma]:
                return None
            cor = self.testes[forma].most_common(1)[0][0]
        acc = self._rgb[forma].get(cor)
        if not (acc and acc[3]):
            return None
        r, g, b = (round(acc[i] / acc[3]) for i in range(3))
        return (r << 16) | (g << 8) | b

   


    #Organiza as formas em ordem crescente do valor hexadecimal RGB da cor
    def ordenar(self, confirmados):
        return sorted(confirmados, key=lambda f: (self.valor_hex(f, confirmados[f][0]), f))