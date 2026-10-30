"""Hash PBKDF2 e recuperação compatíveis com usuários existentes."""
import hashlib, hmac, secrets, random, difflib
from datetime import datetime
from ..config import FORMATO_CRIACAO, ITERACOES_SENHA, ITERACOES_PALAVRA
from .validation import normalizar, novo_id

PALAVRAS_BASE = """
gato pato rato mato fato lato cavalo cabelo castelo camelo cachorro macaco tigre zebra vaca lobo ovelha abelha
coelho joelho vermelho pássaro peixe peito leite leito feito jeito sapo sapato prato prata plano plana pedra
padre perna pessoa fogo fogão jogo logo lago lado mata meta mesa mola mala bala bola sala sola cola copa copo
corpo porto perto porta forte morte norte corte sorte parte carta casa cama cara caro cana capa cada nada roda
rosa rota nuvem chuva luva uva vela vila fila fina fita vida mundo mudo muro maro mapa mala malha palha folha
fralda falda saia seia areia aldeia ideia janela panela tigela cadeira madeira bandeira fronteira ladeira
biscoito mosquito morcego caderno inverno interno eterno verão verde verme verso versão pente dente gente
mente ponte fonte monte morro corro curso curto cinto cinco cisne sino pino fino lixo luxo bicho nicho
carro barro garra jarra farra terra serra guerra perra livro livre litro letra lenha linha limão leão
amor humor dor cor flor sol mel fel mar par luz cruz paz voz nós foz faz feliz raiz juiz giz cais
mesa meta pesa peso passo pássaro paço palco palma calma calça calor valor favor sabor saber sabão
sabor pomar pomba bomba tomba tinta tenta ponta conta canto santo manto tanto quanto
estrela estrelas escola escova esposa espada espelho espeto estudo estudar
tempo tempero templo tropa trovão troco troca trilha trilho trigo trabalho tapete tapeçaria
cidade verdade vontade saudade amizade bondade liberdade beleza certeza tristeza riqueza pobreza
chave chaves clave cravo craque cravos prova pronto ponto pinto
boneca boneco banana bananas barraca barriga barbeiro caneca canoa cenoura cebola
manga mango mesa gaveta garrafa garfo faca foca fica faixa baixa caixa peixe queixa
rádio radio ração razão rasgo rastro rastelo pastel pastor pastora motor moto moda modo molho
tigre trigo trapo trato trato tratado quadro quarto quarta quatro
cheiro cheio chefe cheque chuva chama chave chato chapéu chão
navio nariz nuvem ninho ninhos nome nota noite noiva noivo
orelha ouvido ouro osso ovo olho óculos ombro onda
praia prazo preço pressa prego prego premio prêmio praça
relógio remédio revista rio rua ruído rumo rápido
sapato segredo semana sempre senha sorriso soldado sonho sombra
tambor tarde teatro telhado tesoura tijolo timão tomate torre
vaso vento verão viagem vidro vizinho vulcão
zebra zero zona zelo
""".split()

def hash_texto(texto, salt_hex, iteracoes):
    return hashlib.pbkdf2_hmac("sha256", texto.encode("utf-8"), bytes.fromhex(salt_hex), iteracoes).hex()

def criar_hash(texto, iteracoes):
    salt = secrets.token_hex(16)
    return salt, hash_texto(texto, salt, iteracoes)

def conferir_hash(texto, salt_hex, hash_guardado, iteracoes):
    return hmac.compare_digest(hash_texto(texto, salt_hex, iteracoes), hash_guardado)

def variar_palavra(p):
    """Gera uma variação de escrita da palavra (troca de letra, transposição etc.)."""
    letras = list(p)
    tipo = random.choice(["vogal", "consoante", "transpor", "duplicar", "remover", "sufixo"])
    vogais = "aeiou"
    if tipo == "vogal":
        idx = [i for i, c in enumerate(letras) if c in vogais]
        if idx:
            i = random.choice(idx)
            letras[i] = random.choice([v for v in vogais if v != letras[i]])
    elif tipo == "consoante":
        grupos = ["bpd", "cgqs", "mn", "tdf", "lr", "zsx", "vfb", "jgh"]
        idx = [i for i, c in enumerate(letras) if any(c in g for g in grupos)]
        if idx:
            i = random.choice(idx)
            g = next(g for g in grupos if letras[i] in g)
            letras[i] = random.choice([c for c in g if c != letras[i]])
    elif tipo == "transpor" and len(letras) > 3:
        i = random.randrange(len(letras) - 1)
        letras[i], letras[i + 1] = letras[i + 1], letras[i]
    elif tipo == "duplicar":
        i = random.randrange(len(letras))
        letras.insert(i, letras[i])
    elif tipo == "remover" and len(letras) > 4:
        del letras[random.randrange(len(letras))]
    else:
        return p + random.choice(["s", "a", "o", "e"])
    return "".join(letras)

def gerar_semelhantes(palavra, quantidade=3):
    """Devolve palavras com escrita parecida com a escolhida (para servirem de alternativas A-D)."""
    alvo = normalizar(palavra)
    escolhidas, vistos = [], {alvo}

    # 1) palavras reais parecidas, do dicionário embutido
    pontuadas = []
    for cand in set(PALAVRAS_BASE):
        n = normalizar(cand)
        if n in vistos or abs(len(n) - len(alvo)) > 2:
            continue
        r = difflib.SequenceMatcher(None, alvo, n).ratio()
        if r >= 0.5:
            pontuadas.append((r, cand))
    pontuadas.sort(reverse=True)
    melhores = pontuadas[:8]
    random.shuffle(melhores)
    for _r, cand in melhores:
        if len(escolhidas) == quantidade:
            break
        escolhidas.append(cand)
        vistos.add(normalizar(cand))

    # 2) variações de escrita, se faltou
    tentativas = 0
    while len(escolhidas) < quantidade and tentativas < 300:
        tentativas += 1
        var = variar_palavra(alvo)
        n = normalizar(var)
        if n in vistos or len(n) < 2:
            continue
        escolhidas.append(var)
        vistos.add(n)
    return escolhidas

def montar_usuario(nome, exibicao, email, cpf, cargo, senha, palavras):
    """Cria o dicionário do usuário já com senha e palavras-chave protegidas por hash."""
    salt, h = criar_hash(senha, ITERACOES_SENHA)
    lista_palavras = []
    for p in palavras:
        opcoes = [p] + gerar_semelhantes(p)
        while len(opcoes) < 4:                       # garantia: sempre 4 alternativas (A-D)
            extra = p + random.choice("aeos")
            if normalizar(extra) not in [normalizar(o) for o in opcoes]:
                opcoes.append(extra)
        random.shuffle(opcoes)
        s, hp = criar_hash(normalizar(p), ITERACOES_PALAVRA)
        lista_palavras.append({"Opcoes": opcoes, "Salt": s, "Hash": hp})
    return {
        "Id": novo_id(), "NomeCompleto": nome, "NomeExibicao": exibicao, "Email": email, "CPF": cpf,
        "Cargo": cargo, "SenhaSalt": salt, "SenhaHash": h, "Palavras": lista_palavras,
        "Tentativas": 0, "BloqueadoAte": "", "CriadoEm": datetime.now().strftime(FORMATO_CRIACAO),
    }
