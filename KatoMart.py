# coding=utf-8

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#            Esse script faz parte de um projeto bem maior,                   #
#             solto no momento pq quero feedback, de tudo.                    #
#         Também preciso que ele seja testado contra diversos cursos          #
#               e que os problemas sejam apresentados.                        #
#                      Meu telegram: @katomaro                                #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# Antes de mais nada, instale o FFMPEG no sistema 
# (adicionando-o às variáveis de ambiente)
#
# Após isso, verifique se instalou as dependências listadas abaixo, pelo pip:
# m3u8, beautifulsoup4, youtube_dl
#
# Feito isso, só rodar esse .py

# Features esperadas nessa versão:
#   • Baixa apenas coisas que não tiveram o download completado anteriormente 
#       (com algumas excessões, tipo links.txt)
#   • Se a conexão for perdida em um download do vimeo/youtube, 
#       arquivos residuais ficaram na pasta, devem ser apagados
#   • Ou seja, aulas hospedadas na hotmart, no vimeo e no youtube
#   • Baixa os anexos, salva os links (leitura complementar) e as descrições
#   • Mantém tudo salvo na organização da plataforma
#       (<<DEVE SER VERIFICADA A ORDENAÇÃO DE MÓDULOS)

# Se algo de estranho acontecer ou se precisar de ajuda, chama no telegram.
#
# Possivelmente precisarei dos arquivos "log.txt" e do "debug.txt", 
# saiba que o log na pasta raiz tem info de login usada. 
# Já o "log.txt" dentro da pasta do curso apenas indica as ações do bot,
# fácil para acompanhar junto com o "debug.txt".

import datetime
import glob
import json
import os
import random
import re
import string
import subprocess
import sys
import time

import m3u8
import requests
import youtube_dl

from bs4 import BeautifulSoup
from requests import HTTPError, Timeout
from requests.exceptions import ChunkedEncodingError, ContentDecodingError

from AnsiEscapeCodes import Colors

# GLOBALS
USER_EMAIL = input("Qual o seu Email da Hotmart?\n")
USER_PASS = input("Qual a sua senha da Hotmart?\n")

HOTMART_API = 'https://api-club.hotmart.com/hot-club-api/rest/v3'
CONTENT_TYPE = 'application/json, text/plain, */*'
NO_CACHE = 'no-cache'
ENCODING = "utf-8"

maxCursos = 0
cursoAtual = 1

class Hotmart:
    _USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        ' AppleWebKit/537.36 (KHTML, like Gecko)'
        ' Chrome/91.0.4472.106 Safari/537.36'
    )

    def auth(self, userEmail, userPass):
        authMart = requests.session()
        authMart.headers['user-agent'] = self._USER_AGENT

        data = {
            'username': userEmail,
            'password': userPass,
            'grant_type': 'password'
        }

        GET_TOKEN_URL = 'https://api.sparkleapp.com.br/oauth/token'
        authSparkle = authMart.post(GET_TOKEN_URL, data=data)

        authSparkle = authSparkle.json()

        try:
            authMart.headers.clear()
            authMart.headers['user-agent'] = self._USER_AGENT
            authMart.headers['authorization'] = f"Bearer {authSparkle['access_token']}"
        except KeyError:
            print(f"{Colors.Red}{Colors.Bold}Tentativa de login falhou! Verifique os dados ou contate o @katomaro (Telegram){Colors.Reset}")
            exit(13)
        return authMart

    def getProdutos(self, authMart):
        CHECK_TOKEN_URL = 'https://api-sec-vlc.hotmart.com/security/oauth/check_token'
        TOKEN = authMart.headers['authorization'].split(" ")[1]

        return authMart.get(CHECK_TOKEN_URL, params={'token': TOKEN}) \
            .json()['resources']

    def getCursos(self, authMart):
        produtos = self.getProdutos(authMart)
        cursosValidos = []

        for produto in produtos:
            try:
                if produto['resource']['status'] != "ACTIVE" and "STUDENT" not in produto['roles']:
                    continue

                HOST = produto['resource']['subdomain']
                URL = f'https://{HOST}.club.hotmart.com'

                authMart.headers['origin'] = URL
                authMart.headers['referer'] = URL
                authMart.headers['club'] = HOST

                membership = authMart \
                    .get(f'{HOTMART_API}/membership?attach_token=false') \
                    .json()['name']

                produto["nome"] = limpaString(membership) 

                cursosValidos.append(produto)
            except KeyError:
                continue

        return cursosValidos

hotmart = Hotmart()

def clearScreen():
    if sys.platform.startswith('darwin'):
        # MacOs specific procedures
        os.system("clear")
    elif sys.platform.startswith('win32'):
        # Windows specific procedures
        os.system("cls")

def verCursos():
    authMart = hotmart.auth(USER_EMAIL, USER_PASS)
    cursosValidos = hotmart.getCursos(authMart)

    print("Cursos disponíveis para download:")

    for index, curso in enumerate(cursosValidos, start=1):
        print("\t", index, curso['nome'])

    OPCAO = int(input( f"Qual curso deseja baixar? {Colors.Magenta}(0 para todos!){Colors.Reset}\n")) - 1

    if OPCAO == -1:
        global maxCursos
        maxCursos = len(cursosValidos)

        for curso in cursosValidos:
            baixarCurso(authMart, curso, True)
    else:
        baixarCurso(authMart, cursosValidos[OPCAO], False)

def criaTempFolder():
    CURRENT_FOLDER = os.path.abspath(os.getcwd())
    tempFolder = CURRENT_FOLDER

    while os.path.isdir(tempFolder):
        FOLDER_NAME = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        tempFolder = os.path.join(CURRENT_FOLDER, 'temp', FOLDER_NAME)

        if not os.path.isdir(tempFolder):
            try:
                os.makedirs(tempFolder)
            except:
                pass
            break
    
    return tempFolder

def limpaString(string):
    result = re.sub(r'[<>:!"/\\|?*]', '', string) \
        .strip() \
        .replace('.', '') \
        .replace("\t", "")

    return result

def criaCurso(nome):
    nomeCurso = limpaString(nome)

    pathCurso = os.path.join(
        os.path.abspath(os.getcwd()),
        'Cursos',
        nomeCurso)

    if not os.path.exists(pathCurso):
        try:
            os.makedirs(pathCurso)
        except:
            pass

    return (nomeCurso, pathCurso)

def criaSubDir(parentDir, order, nome):
    cleanName = f"{order}. " + limpaString(nome)

    dirPath = os.path.join(parentDir, cleanName)

    if not os.path.exists(dirPath):
        os.makedirs(dirPath)

    return (cleanName, dirPath)

# TODO Melhorar esse workaround para nome longo
def criaVideo(PATH_CURSO, PATH_AULA, index):
    videoPath = os.path.join(PATH_AULA , f"aula-{index}.mp4")
    evPath = os.path.join(PATH_CURSO , "ev")

    if len(videoPath) > 254:
        if not os.path.exists(evPath):
            os.makedirs(evPath)

        tempName = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        listPath = os.path.join(evPath , "list.txt")

        with open(listPath, "a", encoding=ENCODING) as safelist:
            safelist.write(f"{tempName} = {videoPath}\n")

        videoPath = os.path.join(evPath , f"{tempName}.mp4")

    return videoPath

def getInfoAula(authMart, dominio, url, hash):
    #  TODO Melhorar isso lol
    infoAula = None

    while True:
        try:
            infoAula = authMart \
                .get(f'{HOTMART_API}/page/{hash}') \
                .json()
            break
        except (HTTPError, ConnectionError, Timeout, ChunkedEncodingError, ContentDecodingError):
            authMart = hotmart.auth(USER_EMAIL, USER_PASS)
            authMart.headers['accept'] = CONTENT_TYPE
            authMart.headers['origin'] = url
            authMart.headers['referer'] = url
            authMart.headers['club'] = dominio
            authMart.headers['pragma'] = NO_CACHE
            authMart.headers['cache-control'] = NO_CACHE
            continue

    return infoAula

def getPlayerInfo(authMart, media):
    playerData = authMart.get(media['mediaSrcUrl']).text

    # Descomentar para ver o que caralhos a plataforma retorna do player
    # with open("player.html", "w") as phtml:
    #     phtml.write(playerData)

    playerDom = BeautifulSoup(playerData, features="html.parser")
    playerConfigurations = playerDom \
        .find(text=re.compile("window.playerConfig"))[:-1]
    playerConfigJson = playerConfigurations.split(" ", 2)[2]
    playerInfo = json.loads(playerConfigJson)

    return playerInfo['player']

def baixarCurso(authMart, infoCurso, downloadAll):
    TEMP_FOLDER = criaTempFolder()
    NOME_CURSO, PATH_CURSO = criaCurso(infoCurso['nome'])
    
    clearScreen()

    if downloadAll:
        global maxCursos
        global cursoAtual

        print(f"{Colors.Magenta}Modo de download de todos os cursos! {cursoAtual}/{maxCursos}")
        cursoAtual += 1

    DOMINIO = infoCurso['resource']['subdomain']
    URL = f"https://{DOMINIO}.club.hotmart.com/"

    youtube_dl.utils.std_headers['Referer'] = URL

    authMart.headers['accept'] = CONTENT_TYPE
    authMart.headers['origin'] = URL
    authMart.headers['referer'] = URL
    authMart.headers['club'] = DOMINIO
    authMart.headers['pragma'] = NO_CACHE
    authMart.headers['cache-control'] = NO_CACHE

    curso = authMart.get(f'{HOTMART_API}/navigation').json()

    print(f"Baixando o curso: {Colors.Cyan}{Colors.Bold}{NOME_CURSO}{Colors.Reset} (pressione {Colors.Magenta}ctrl+c{Colors.Reset} a qualquer momento para {Colors.Red}cancelar{Colors.Reset})")
    
    # Descomentar para ver o que caralhos a plataforma dá de json de curso
    # with open('data.json', 'w', encoding=ENCODING) as f:
    #     json.dump(curso, f, ensure_ascii=False, indent=4)

    moduleCount = 0
    lessonCount = 0

    vidCount = 0
    videosLongos = 0
    videosInexistentes = 0
    segVideos = 0
    
    descCount = 0
    attCount = 0
    linkCount = 0
    descLongas = 0
    linksLongos = 0
    anexosLongos = 0

    try:
        for modulo in curso['modules']:
            NOME_MODULO, PATH_MODULO = criaSubDir(PATH_CURSO, modulo['moduleOrder'], modulo['name'])

            moduleCount += 1
            for aula in modulo['pages']:
                NOME_AULA, PATH_AULA = criaSubDir(PATH_MODULO, aula['pageOrder'], aula['name'])

                print(f"{Colors.Magenta}Tentando baixar a aula: {Colors.Cyan}{NOME_MODULO}{Colors.Magenta}/{Colors.Green}{NOME_AULA}{Colors.Magenta}!{Colors.Reset}")

                lessonCount += 1
                infoAula = getInfoAula(authMart, DOMINIO, URL, aula["hash"])

                # Descomentar para ver o que caralhos a plataforma retorna na página
                # with open('aula.json', 'w', encoding=ENCODING) as f:
                #     json.dump(infoAula, f, ensure_ascii=False, indent=4)

                # Download Aulas Nativas (HLS)
                tryDL = 2
                while tryDL:
                    try:
                        try:
                            for index, media in enumerate(infoAula['mediasSrc'], start=1):
                                if media['mediaType'] != "VIDEO":
                                    continue

                                print(f"\t{Colors.Magenta}Tentando baixar o vídeo {index}{Colors.Reset}")

                                playerInfo = getPlayerInfo(authMart, media)
                                segVideos += playerInfo['mediaDuration']

                                for asset in playerInfo['assets']:
                                    videoPath = criaVideo(PATH_CURSO, PATH_AULA, index)

                                    # TODO Melhorar esse workaround para nome longo
                                    if len(videoPath) > 254:
                                        videosLongos += 1

                                    success = None

                                    if not os.path.isfile(videoPath):
                                        success = downloadVideoNativo(authMart, TEMP_FOLDER, NOME_MODULO, NOME_AULA, playerInfo, asset)
                                    else:
                                        print("VIDEO JA EXISTE")
                                        success = True

                                    if success:
                                        vidCount += 1
                                # tryDL = 0

                        # Download de aula Externa
                        except KeyError:
                            videos, videosLongos, videosInexistentes = downloadVideoExterno(PATH_CURSO, PATH_AULA, NOME_CURSO, NOME_MODULO, NOME_AULA, infoAula)
                            vidCount += videos

                        # Count Descrições
                        try:
                            if infoAula['content']:
                                # TODO Mesmo trecho de aula longa zzz

                                filePath = os.path.dirname(
                                    os.path.abspath(__file__))
                                videoPath = f"{filePath}/Cursos/{NOME_CURSO}/{NOME_MODULO}/{NOME_AULA}/desc.html"
                                if len(videoPath) > 254:
                                    if not os.path.exists(f"Cursos/{NOME_CURSO}/ed"):
                                        os.makedirs(f"Cursos/{NOME_CURSO}/ed")
                                    tempNM = ''.join(random.choices(
                                        string.ascii_uppercase + string.digits, k=8))
                                    with open(f"Cursos/{NOME_CURSO}/ed/list.txt", "a", encoding=ENCODING) as safelist:
                                        safelist.write(
                                            f"{tempNM} = {NOME_CURSO}/{NOME_MODULO}/{NOME_AULA}/desc.html\n")
                                    videoPath = f"Cursos/{NOME_CURSO}/ed/{tempNM}.html"
                                    descLongas += 1

                                if not os.path.isfile(f"{videoPath}"):
                                    with open(f"{videoPath}", "w", encoding=ENCODING) as desct:
                                        desct.write(infoAula['content'])
                                        print(
                                            f"{Colors.Magenta}Descrição da aula salva!{Colors.Reset}")
                                descCount += 1

                        except KeyError:
                            pass

                        # Count Anexos
                        try:
                            for att in infoAula['attachments']:
                                print(
                                    f"{Colors.Magenta}Tentando baixar o anexo: {Colors.Red}{att['fileName']}{Colors.Reset}")
                                # TODO Mesmo trecho de aula longa zzz

                                filePath = os.path.dirname(
                                    os.path.abspath(__file__))
                                videoPath = f"{filePath}/Cursos/{NOME_CURSO}/{NOME_MODULO}/{NOME_AULA}/Materiais/{att['fileName']}"
                                if len(videoPath) > 254:
                                    if not os.path.exists(f"Cursos/{NOME_CURSO}/et"):
                                        os.makedirs(f"Cursos/{NOME_CURSO}/et")
                                    tempNM = ''.join(random.choices(
                                        string.ascii_uppercase + string.digits, k=8))
                                    with open(f"Cursos/{NOME_CURSO}/et/list.txt", "a", encoding=ENCODING) as safelist:
                                        safelist.write(
                                            f"{tempNM} = {NOME_CURSO}/{NOME_MODULO}/{NOME_AULA}/Materiais/{att['fileName']}\n")
                                    videoPath = f"Cursos/{NOME_CURSO}/et/{tempNM}.{att['fileName'].split('.')[-1]}"
                                    anexosLongos += 1

                                try:
                                    if not os.path.exists(f"Cursos/{NOME_CURSO}/{NOME_MODULO}/{NOME_AULA}/Materiais"):
                                        os.makedirs(
                                            f"Cursos/{NOME_CURSO}/{NOME_MODULO}/{NOME_AULA}/Materiais")
                                except:
                                    pass

                                if not os.path.isfile(f"{videoPath}"):
                                    while True:
                                        try:
                                            try:
                                                attGetter = authMart
                                                anexo = attGetter.get(
                                                    f"{HOTMART_API}/attachment/{att['fileMembershipId']}/download").json()
                                                anexo = requests.get(
                                                    anexo['directDownloadUrl'])
                                            except KeyError:
                                                vrum = requests.session()
                                                vrum.headers.update(
                                                    authMart.headers)
                                                lambdaUrl = anexo['lambdaUrl']
                                                vrum.headers['token'] = anexo['token']
                                                anexo = requests.get(
                                                    vrum.get(lambdaUrl).text)
                                                del vrum
                                            with open(f"{videoPath}", 'wb') as ann:
                                                ann.write(anexo.content)
                                                print(
                                                    f"{Colors.Magenta}Anexo baixado com sucesso!{Colors.Reset}")
                                            break
                                        except:
                                            pass
                                attCount += 1
                        except KeyError:
                            pass

                        # Count Links Complementares
                        try:
                            if infoAula['complementaryReadings']:
                                # TODO Mesmo trecho de aula longa zzz

                                filePath = os.path.dirname(
                                    os.path.abspath(__file__))
                                videoPath = f"{filePath}/Cursos/{NOME_CURSO}/{NOME_MODULO}/{NOME_AULA}/links.txt"
                                if len(videoPath) > 254:
                                    if not os.path.exists(f"Cursos/{NOME_CURSO}/el"):
                                        os.makedirs(f"Cursos/{NOME_CURSO}/el")
                                    tempNM = ''.join(random.choices(
                                        string.ascii_uppercase + string.digits, k=8))
                                    with open(f"Cursos/{NOME_CURSO}/el/list.txt", "a", encoding=ENCODING) as safelist:
                                        safelist.write(
                                            f"{tempNM} = {NOME_CURSO}/{NOME_MODULO}/{NOME_AULA}/links.txt\n")
                                    videoPath = f"Cursos/{NOME_CURSO}/el/links.txt"
                                    linksLongos += 1

                                if not os.path.isfile(f"{videoPath}"):
                                    print(
                                        f"{Colors.Magenta}Link Complementar encontrado!{Colors.Reset}")
                                    for link in infoAula['complementaryReadings']:
                                        with open(f"{videoPath}", "a", encoding=ENCODING) as linkz:
                                            linkz.write(f"{link}\n")

                                else:
                                    print(
                                        f"{Colors.Green}Os Links já estavam presentes!{Colors.Reset}")
                            linkCount += 1
                        except KeyError:
                            pass

                    except (HTTPError, ConnectionError, Timeout, ChunkedEncodingError, ContentDecodingError):
                        authMart = hotmart.auth(USER_EMAIL, USER_PASS)
                        authMart.headers['accept'] = CONTENT_TYPE
                        authMart.headers['origin'] = URL
                        authMart.headers['referer'] = URL
                        authMart.headers['club'] = DOMINIO
                        authMart.headers['pragma'] = NO_CACHE
                        authMart.headers['cache-control'] = NO_CACHE
                        tryDL -= 1
                        continue
                    break
    except KeyError:
        print(f"\t{Colors.Red}Recurso sem módulos!{Colors.Reset}")

    with open(f"Cursos/{NOME_CURSO}/info.txt", "w", encoding=ENCODING) as nfo:
        nfo.write(f"""Info sobre o rip do curso: {NOME_CURSO} ({URL})
    Data do rip: {datetime.datetime.today().strftime('%d/%m/%Y')}
    Quantidade de recursos/erros (na run que completou):
        Quantidade de Módulos: {moduleCount};
        Quantidade de Aulas: {lessonCount};
        Quantidade de Vídeos: {vidCount}/{videosLongos}, inexistentes: {videosInexistentes};
            Duração (Aproximada, HLS apenas): {segVideos} segundos;
        Quantidade de Descrições(/aulas texto): {descCount}/{descLongas};
        Quantidade de Leitura Complementar: {linkCount}/{linksLongos};
        Quantidade de Anexos: {attCount}/{anexosLongos};

    Caso você esteja vendo algum erro qualquer, entenda:
        Estes erros se referem apenas à erros relacionados à caminhos muito longos, por limitação do sistema de arquivos
        Neste caso, uma pasta chamda "eX" foi criada e o arquivo foi salvo dentro dela com um nome aleatório
        No lugar de X vai uma letra para o que deu erro, sendo "v" para vídeo, "d" para descrição "l" para link
        e "t" para anexo. Dentro da pasta existe um arquivo .txt com a função de te informar onde cada arquivo deveria estar
        e com qual nome. Sinta-se livre de reornigazar e encurtar nomes para deixar organizado, ou não :)

    Vídeos Inexistentes são Lives Agendadas no Youtube, ou, vídeos que foram apagado de onde estavam hospedados.
    Verifique o arquivo "erros.txt", caso exista.
    
    A duração aproximada se refere aos segundos que o player nativo da Hotmart diz para cada aula, não contabilizando aulas do Vimeo/Youtube.

    Run que completou se refere à execução do script que terminou o download.

    A enumeração pode parecer estar faltando coisas, mas geralmente não está, a hotmart que a entrega de forma cagada.

    Script utilizado para download feito por Katinho ;)
    Versão do script: 3.8.4""")

    for f in glob.glob(f"{TEMP_FOLDER}/*"):
        os.remove(f)

    time.sleep(3)

    os.rmdir(TEMP_FOLDER)

    if not downloadAll:
        verCursos()


def downloadVideoExterno(pathCurso, pathAula, nomeCurso, nomeModulo, NomeAula, infoAula):
    try:
        fonteExterna = None
        videosLongos = 0
        videosInexistentes = 0
        vidCount = 0

        content = BeautifulSoup(infoAula['content'], features="html.parser")
        iFrames = content.findAll("iframe")

        for index, iFrame in enumerate(iFrames, start=1):
            # TODO Mesmo trecho de aula longa
            videoPath = criaVideo(pathCurso, pathAula, index)

            # TODO Melhorar esse workaround para nome longo
            if len(videoPath) > 254:
                videosLongos += 1

            if not os.path.isfile(videoPath):
                ydl_opts = {"format": "best",
                            'retries': 3,
                            'fragment_retries': 5,
                            'quiet': True,
                            "outtmpl": f"{videoPath}"}

                if 'player.vimeo' in iFrame.get("src"):
                    fonteExterna = f"{Colors.Cyan}Vimeo{Colors.Reset}"

                    if "?" in iFrame.get("src"):
                        videoLink = iFrame.get("src").split("?")[0]
                    else:
                        videoLink = iFrame.get("src")

                    if videoLink[-1] == "/":
                        videoLink = videoLink.split("/")[-1]

                elif 'vimeo.com' in iFrame.get("src"):
                    fonteExterna = f"{Colors.Cyan}Vimeo{Colors.Reset}"
                    vimeoID = iFrame.get("src").split('vimeo.com/')[1]

                    if "?" in vimeoID:
                        vimeoID = vimeoID.split("?")[0]

                    videoLink = "https://player.vimeo.com/video/" + vimeoID

                elif "wistia.com" in iFrame.get("src"):
                    # TODO Implementar Wistia
                    fonteExterna = None
                    # fonteExterna = f"{C.Yellow}Wistia{C.Reset}"
                    # Preciso de um curso que tenha aula do Wistia para ver como tá sendo dado
                    # :( Ajuda noix Telegram: @katomaro
                    raise KeyError

                elif "youtube.com" in iFrame.get("src") or "youtu.be" in iFrame.get("src"):
                    fonteExterna = f"{Colors.Red}YouTube{Colors.Reset}"
                    videoLink = iFrame.get("src")

                if fonteExterna is not None:
                    print(f"{Colors.Magenta}Baixando aula externa de fonte: {fonteExterna}!")

                    try:
                        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([videoLink])
                        vidCount += 1

                        # TODO especificar os erros de Live Agendada(YouTube) e Video Inexistente
                    except:
                        print(f"{Colors.Red}O vídeo é uma Live Agendada, ou, foi apagado!{Colors.Reset}")

                        errorPath = os.path.join(pathCurso, "erros.txt")
                        with open(errorPath, "a", encoding=ENCODING) as elog:
                            elog.write( f"{videoLink} - {nomeCurso}/{nomeModulo}/{NomeAula}")

                        videosInexistentes += 1
            else:
                vidCount += 1

                # tryDL = 0

    except KeyError:
        print(f"{Colors.Bold}{Colors.Red}Ué, erro ao salvar essa aula, pulada!{Colors.Reset} (verifique se ela tem vídeo desbloqueado na plataforma)")
        tryDL = 0

    return vidCount, videosLongos, videosInexistentes


def downloadVideoNativo(authMart, tempFolder, nomeModulo, nomeAula, playerInfo, asset):
    try:
        videoData = authMart.get(
            f"{asset['url']}?{playerInfo['cloudFrontSignature']}")
        masterPlaylist = m3u8.loads(videoData.text)
        res = []
        highestQual = None
        for playlist in masterPlaylist.playlists:
            res.append(
                playlist.stream_info.resolution)
        res.sort(reverse=True)
        for playlist in masterPlaylist.playlists:
            if playlist.stream_info.resolution == res[0]:
                highestQual = playlist.uri
        if highestQual is not None:
            videoData = authMart.get(
                f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual}?{playerInfo['cloudFrontSignature']}")
            with open(f'{tempFolder}/dump.m3u8', 'w') as dump:
                dump.write(videoData.text)
            videoPlaylist = m3u8.loads(
                videoData.text)
            key = videoPlaylist.segments[0].key.uri
            totalSegmentos = videoPlaylist.segments[-1].uri.split(".")[
                0].split("-")[1]
            for segment in videoPlaylist.segments:
                print(f"\r\tBaixando o segmento {Colors.Blue}{segment.uri.split('.')[0].split('-')[1]}{Colors.Reset}/{Colors.Magenta}{totalSegmentos}{Colors.Reset}!",
                    end="", flush=True)
                uri = segment.uri
                frag = authMart.get(
                    f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual.split('/')[0]}/{uri}?{playerInfo['cloudFrontSignature']}")
                with open(f"{tempFolder}/" + uri, 'wb') as sfrag:
                    sfrag.write(
                        frag.content)
            fragkey = authMart.get(
                f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual.split('/')[0]}/{key}?{playerInfo['cloudFrontSignature']}")
            with open(f"{tempFolder}/{key}", 'wb') as skey:
                skey.write(fragkey.content)
            print(
                f"\r\tSegmentos baixados, gerando video final! {Colors.Red}(dependendo da config do pc este passo pode demorar até 20 minutos!){Colors.Reset}", end="\n", flush=True)

            # TODO Implementar verificação de hardware acceleration
            # ffmpegcmd = f'ffmpeg -hide_banner -loglevel error -v quiet -stats -allowed_extensions ALL -hwaccel cuda -i {tempFolder}/dump.m3u8 -c:v h264_nvenc -n "{aulaPath}"'

            ffmpegcmd = f'ffmpeg -hide_banner -loglevel error -v quiet -stats -allowed_extensions ALL -i {tempFolder}/dump.m3u8 -n "{aulaPath}"'

            if sys.platform.startswith('darwin'):
                # MacOs specific procedures
                subprocess.run(
                    ffmpegcmd, shell=True)
            elif sys.platform.startswith('win32'):
                # Windows specific procedures
                subprocess.run(ffmpegcmd)

                # TODO Implementar verificação de falha pelo FFMPEG
                # p = subprocess.run(ffmpegcmd)
                # if p.returncode != 0:
                #     pass

            print(
                f"Download da aula {Colors.Bold}{Colors.Magenta}{nomeModulo}/{nomeAula}{Colors.Reset} {Colors.Green}concluído{Colors.Reset}!")
            time.sleep(3)
            for ff in glob.glob(f"{tempFolder}/*"):
                os.remove(ff)

        else:
            print(
                f"{Colors.Red}{Colors.Bold}Algo deu errado ao baixar a aula, redefinindo conexão para tentar novamente!{Colors.Reset}")
            raise HTTPError
    except:
        return False

    return True

clearScreen()
verCursos()
