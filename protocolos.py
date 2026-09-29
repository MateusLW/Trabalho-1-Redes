import struct
import zlib

FORMATO_CABECALHO = "!BII"
TAM_CABECALHO = struct.calcsize(FORMATO_CABECALHO)

TAM_PAYLOAD = 1024

TIPO_DADOS = 1
TIPO_ERRO = 2
TIPO_FIM = 3
TIPO_ACK = 4

def empacotar(tipo, num_seq, checksum, dados=b""):
    
    cabecalho = struct.pack(FORMATO_CABECALHO, tipo, num_seq, checksum)
    return cabecalho + dados

def desempacotar(pacote):
    
    cabecalho = pacote[:TAM_CABECALHO]
    dados = pacote[TAM_CABECALHO:]
    
    try:    
        tipo, num_seq, checksum = struct.unpack(FORMATO_CABECALHO, cabecalho)
    except struct.error:
        return None
    
    return tipo, num_seq, checksum, dados

def calcular_checksum(dados):
    return zlib.crc32(dados) & 0xFFFFFFFF

def interpretar_requisicao(dados):
    
    texto = dados.decode("utf-8", errors = "ignore")
    partes = texto.strip().split()
    
    if len(partes) != 2 or partes[0] != "GET":
        return None
    
    caminho = partes[1].lstrip("/")
    return caminho