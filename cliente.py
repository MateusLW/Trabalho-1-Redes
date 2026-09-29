import socket
import re
from tkinter import Tk
from tkinter.filedialog import asksaveasfilename
from protocolos import calcular_checksum, desempacotar, empacotar, TIPO_DADOS, TIPO_ERRO, TIPO_FIM, TIPO_ACK

TIMEOUT = 3.0
MAX_TENTATIVAS = 5

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(TIMEOUT)

entrada_conexao = input("Digite o endereco no formato @IP:Porta/arquivo.ext: ")

padrao = r"^@([\d.]+):(\d+)/(.+)$"
correspondencia = re.match(padrao, entrada_conexao.strip())

if not correspondencia:
    print("Formato invalido. Use: @IP:Porta/arquivo.ext")
    exit()

HOST_SERVIDOR = correspondencia.group(1)
PORTA_SERVIDOR = int(correspondencia.group(2))
nome_arquivo = correspondencia.group(3)

requisicao = f"GET /{nome_arquivo}".encode("utf-8")

entrada = input("Digite os numeros de blocos para descartar (separados por virgula, ou Enter para nenhum): ")

if entrada.strip():
    blocos_ignorar = set(int(x.strip()) for x in entrada.split(","))
else:
    blocos_ignorar = set()
    
sock.sendto(requisicao, (HOST_SERVIDOR, PORTA_SERVIDOR))

blocos = {}
recebendo = True
erro = False
tentativas = 0

while recebendo:
    
    try:
        pacote, origem = sock.recvfrom(2048)
        tentativas = 0
    except socket.timeout:
        tentativas += 1
        print(f"Sem resposta do servidor, tentativa {tentativas}/{MAX_TENTATIVAS}")
        if tentativas >= MAX_TENTATIVAS:
            print("Servidor nao respondeu apos varias tentativas, encerrando")
            erro = True
            recebendo = False
        continue
    
    resultado = desempacotar(pacote)
    
    if resultado is None:
        print("Pacote malformado, ignorando")
        continue
    
    tipo, num_seq, checksum, dados = resultado
    
    if tipo == TIPO_ERRO:
        print(f"Erro do servidor: {dados.decode("utf-8", errors="ignore")}")
        recebendo = False
        erro = True
    
    elif tipo == TIPO_DADOS:
        checksum_calculado = calcular_checksum(dados) 
        
        if checksum == checksum_calculado:
            
            if num_seq in blocos_ignorar:
                print(f"Simulando perda: descartando bloco {num_seq} de proposito")
                blocos_ignorar.discard(num_seq)
                continue
            
            blocos[num_seq] = dados
            
            ack = empacotar(TIPO_ACK, num_seq, 0)
            sock.sendto(ack, origem)
            print(f"Bloco {num_seq} recebido")
        
        
        else:
            print(f"Bloco {num_seq} corrompido, descartado")
    
    elif tipo == TIPO_FIM:
        recebendo = False
        print("Fim dos dados")

if erro:
    print("Processo abortado")
    
else:
    numeros_ordenados = sorted(blocos.keys())
    conteudo_final = b"".join(blocos[n] for n in numeros_ordenados)

    root = Tk()
    root.withdraw()
    caminho_salvar = asksaveasfilename(
        title="Salvar arquivo recebido",
        initialfile=nome_arquivo
    )
    root.destroy()

    if caminho_salvar:
        with open(caminho_salvar, "wb") as f:
            f.write(conteudo_final)
        print(f"Arquivo salvo em: {caminho_salvar} ({len(conteudo_final)} bytes, {len(blocos)} blocos)")
    else:
        print("Usuario cancelou o salvamento")