import socket
import os
import threading
import time
from protocolos import empacotar, desempacotar, interpretar_requisicao, calcular_checksum, TIPO_DADOS, TIPO_ERRO, TIPO_FIM, TIPO_ACK, TAM_PAYLOAD

HOST = "0.0.0.0"
PORTA = 5000
PASTA_ARQUIVOS =  "arquivos_servidor"

TIMEOUT = 1.0
MAX_TENTATIVAS = 5
DELAY_TESTE = 0

print("Conectando no servidor UDP")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORTA))

print(f"Servidor UDP conectado em {HOST}:{PORTA}")

def atendendo_cliente(nome_arquivo, endereco):
    
    sock_cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_cliente.settimeout(TIMEOUT)
    
    caminho_completo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
    
    if not os.path.isfile(caminho_completo):
        
        print(f"Arquivo {nome_arquivo} nao foi encontrado")
        
        erro = empacotar(TIPO_ERRO, 0, 0, b"Arquivo nao encontrado")
        sock_cliente.sendto(erro, endereco)
        
        return
    
    print(f"Enviando {nome_arquivo} para {endereco}")
    
    with open(caminho_completo, "rb") as f:
        arquivo = f.read()
    
    num_seq = 0
    transferencia_abortada = False
    for i in range(0, len(arquivo), TAM_PAYLOAD):
        
        bloco = arquivo[i:i + TAM_PAYLOAD]
        checksum = calcular_checksum(bloco)
        
        pacote = empacotar(TIPO_DADOS, num_seq, checksum, bloco)
        
        confirmado = False
        tentativas = 0

        while not confirmado and tentativas < MAX_TENTATIVAS:
            sock_cliente.sendto(pacote, endereco)
            try:
                resposta, origem = sock_cliente.recvfrom(2048)
                resultado = desempacotar(resposta)
                
                if resultado is None:
                    print("Pacote malformado, ignorando")
                    continue
                
                ack_tipo, ack_num_seq, ack_checksum, ack_dados = resultado

                if ack_tipo == TIPO_ACK and ack_num_seq == num_seq and origem == endereco:
                    confirmado = True
                else:
                    print(f"ACK inesperado ou de outro cliente, ignorando")
                    continue

            except socket.timeout:
                tentativas += 1
                print(f"Timeout no bloco {num_seq}, tentativa {tentativas}/{MAX_TENTATIVAS}")

        if not confirmado:
            erro = empacotar(TIPO_ERRO, num_seq, 0, b"Transferencia abortada: cliente nao respondeu")
            sock_cliente.sendto(erro, endereco)
            transferencia_abortada = True
            print(f"Bloco {num_seq} falhou apos {MAX_TENTATIVAS} tentativas, abortando")
            break
        
        num_seq += 1
        time.sleep(DELAY_TESTE)
    
    if not transferencia_abortada:
        final = empacotar(TIPO_FIM, num_seq, 0)
        sock_cliente.sendto(final, endereco)
    
    print(f"Arquivo enviado em {num_seq} blocos")

while(True):
    dado, endereco = sock.recvfrom(2048)
    
    nome_arquivo = interpretar_requisicao(dado)
    
    if nome_arquivo is None:
        continue
    
    nome_arquivo = os.path.basename(nome_arquivo)
    print(f"{endereco} solicitou: {nome_arquivo}")
    
    thread = threading.Thread(target=atendendo_cliente, args=(nome_arquivo, endereco), daemon=True)
    thread.start()
