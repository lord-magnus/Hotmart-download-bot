# coding=utf-8

from __future__ import annotations

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
from requests.sessions import Session
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

    def __init__(self, userEmail, userPass) -> None:
        self._authMart: Session = self._auth(userEmail, userPass)

    def _auth(self, userEmail, userPass) -> Session:
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
            print(f"{Colors.Red}{Colors.Bold}Tentativa de login falhou! Verifique o repositório em https://github.com/katomaro/Hotmart-download-bot{Colors.Reset}")
            exit(13)

        return authMart

    def getProdutos(self):
        CHECK_TOKEN_URL = 'https://api-sec-vlc.hotmart.com/security/oauth/check_token'
        TOKEN = self._authMart.headers['authorization'].split(" ")[1]

        checkToken = self.get(CHECK_TOKEN_URL, params={'token': TOKEN}).json()
        return checkToken['resources']

    def getCursos(self) -> list[CursoHotmart]:
        produtos = self.getProdutos()
        cursosValidos: list[CursoHotmart] = []

        for produto in produtos:
            try:
                curso = CursoHotmart(self, produto)
                if curso.STATUS != "ACTIVE" and "STUDENT" not in curso.ROLES:
                    continue

                cursosValidos.append(curso)
            except KeyError:
                continue

        return cursosValidos

    def getPlayerInfo(self, media):
        playerData = self.get(media['mediaSrcUrl']).text

        # Descomentar para ver o que caralhos a plataforma retorna do player
        # with open("player.html", "w") as phtml:
        #     phtml.write(playerData)

        playerDom = BeautifulSoup(playerData, features="html.parser")
        configPattern = re.compile("window.playerConfig")
        playerConfigurations = playerDom .find(text = configPattern)[:-1]
        playerConfigJson = playerConfigurations.split(" ", 2)[2]
        playerInfo = json.loads(playerConfigJson)

        return playerInfo['player']

    def get(self, url, params = None):
        return self._authMart.get(url, params = params)

    def setHeaders(self, infoCurso: CursoHotmart):
        self._authMart.headers['accept'] = CONTENT_TYPE
        self._authMart.headers['origin'] = infoCurso._URL
        self._authMart.headers['referer'] = infoCurso._URL
        self._authMart.headers['club'] = infoCurso._HOST
        self._authMart.headers['pragma'] = NO_CACHE
        self._authMart.headers['cache-control'] = NO_CACHE

    def getHeaders(self):
        return self._authMart.headers

    def getAttachment(self, att):
        try:
            anexo = self.get(f"{HOTMART_API}/attachment/{att['fileMembershipId']}/download").json()
            anexo = requests.get(anexo['directDownloadUrl'])
        except KeyError:
            vrum = requests.session()
            vrum.headers.update(hotmart.getHeaders())
            lambdaUrl = anexo['lambdaUrl']
            vrum.headers['token'] = anexo['token']
            anexo = requests.get(vrum.get(lambdaUrl).text)
            del vrum
        return anexo

class AulaHotmart:
    def __init__(self, hotmart: Hotmart, path, aula) -> None:
        self.ORDER: int = aula['pageOrder']
        self.NAME: string = limpaString(aula['name'])
        self.FULL_NAME: string = f"{self.ORDER}. " + self.NAME
        self.HASH: string = aula["hash"]
        self.BASE_PATH: string = path
        self.PATH: string = criaSubDir(path, self.FULL_NAME)

        self._HOTMART: Hotmart = hotmart

    def getInfo(self, infoCurso: CursoHotmart, hash):
        infoAula = None

        while True:
            try:
                self._HOTMART.setHeaders(infoCurso)
                infoAula = self._HOTMART.get(f'{HOTMART_API}/page/{hash}').json()
                break
            except (HTTPError, ConnectionError, Timeout, ChunkedEncodingError, ContentDecodingError):
                self._authMart = self._HOTMART._auth(USER_EMAIL, USER_PASS)
                self._HOTMART.setHeaders(infoCurso)
                continue

        return infoAula

class ModuloHotmart:
    def __init__(self, hotmart: Hotmart, path, modulo) -> None:
        self.ORDER: int = modulo['moduleOrder']
        self.NAME: string = limpaString(modulo['name'])
        self.FULL_NAME: string = f"{self.ORDER}. " + self.NAME
        self.BASE_PATH: string = path
        self.PATH: string = criaSubDir(path, self.FULL_NAME)
        self.AULAS: list[AulaHotmart] = []
        self._HOTMART: Hotmart = hotmart

        for aulaInfo in modulo['pages']:
            try:
                aula = AulaHotmart(hotmart, self.PATH, aulaInfo)
                
                self.AULAS.append(aula)
            except KeyError:
                continue

class CursoHotmart:
    def __init__(self, hotmart: Hotmart, product) -> None:
        self.STATUS: string = product['resource']['status']
        self.ROLES: string = product['roles']
        self._HOST: string = product['resource']['subdomain']
        self._URL: string = f'https://{self._HOST}.club.hotmart.com'
        self.MODULOS: list[ModuloHotmart] = []

        youtube_dl.utils.std_headers['Referer'] = self._URL
        
        hotmart.setHeaders(self)
        membership = hotmart \
                    .get(f'{HOTMART_API}/membership?attach_token=false') \
                    .json()

        self.NOME = limpaString(membership['name'])
        self.PATH = criaCurso(self.NOME)

        hotmart.setHeaders(self)
        curso = hotmart.get(f'{HOTMART_API}/navigation').json()

        for moduloInfo in curso['modules']:
            try:
                modulo = ModuloHotmart(hotmart, self.PATH, moduloInfo)
                
                self.MODULOS.append(modulo)
            except KeyError:
                continue

hotmart = Hotmart(USER_EMAIL, USER_PASS)

def clearScreen():
    if sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
        # MacOs specific procedures
        os.system("clear")
    elif sys.platform.startswith('win32'):
        # Windows specific procedures
        os.system("cls")

def verCursos():
    cursosValidos: list[CursoHotmart] = hotmart.getCursos()

    print("Cursos disponíveis para download:")

    for index, curso in enumerate(cursosValidos, start=1):
        print("\t", index, curso.NOME)

    OPCAO = int(input( f"Qual curso deseja baixar? {Colors.Magenta}(0 para todos!){Colors.Reset}\n")) - 1

    if OPCAO == -1:
        global maxCursos
        maxCursos = len(cursosValidos)

        for curso in cursosValidos:
            baixarCurso(curso, True)
    else:
        baixarCurso(cursosValidos[OPCAO], False)

def baixarCurso(infoCurso: CursoHotmart, downloadAll):
    TEMP_FOLDER = criaTempFolder()
    
    clearScreen()

    if downloadAll:
        global maxCursos
        global cursoAtual

        print(f"{Colors.Magenta}Modo de download de todos os cursos! {cursoAtual}/{maxCursos}")
        cursoAtual += 1

    print(f"Baixando o curso: {Colors.Cyan}{Colors.Bold}{infoCurso.NOME}{Colors.Reset} (pressione {Colors.Magenta}ctrl+c{Colors.Reset} a qualquer momento para {Colors.Red}cancelar{Colors.Reset})")
    
    # Descomentar para ver o que caralhos a plataforma dá de json de curso
    # with open('data.json', 'w', encoding=ENCODING) as f:
    #     json.dump(curso, f, ensure_ascii=False, indent=4)

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
        for modulo in infoCurso.MODULOS:
            for aula in modulo.AULAS:
                print(f"{Colors.Magenta}Tentando baixar a aula: {Colors.Cyan}{modulo.FULL_NAME}{Colors.Magenta}/{Colors.Green}{aula.FULL_NAME}{Colors.Magenta}!{Colors.Reset}")

                lessonCount += 1
                infoAula = aula.getInfo(infoCurso, aula.HASH)

                # Descomentar para ver o que caralhos a plataforma retorna na página
                # with open('aula.json', 'w', encoding=ENCODING) as f:
                #     json.dump(infoAula, f, ensure_ascii=False, indent=4)

                # Download Aulas Nativas (HLS)
                tryDL = 2

                while tryDL:
                    try:
                        try:
                            videos, videosLongos, segVideos = downloadVideos(TEMP_FOLDER, modulo.PATH, modulo.FULL_NAME, aula.FULL_NAME, aula.PATH, infoAula)
                            vidCount += videos
                            pass

                        # Download de aula Externa
                        except KeyError:
                           videos, videosLongos, videosInexistentes = downloadVideoExterno(modulo.PATH, infoCurso.NOME, modulo.FULL_NAME, aula.FULL_NAME, infoAula)
                           vidCount += videos
                           pass

                        # Count Descrições
                        try:
                            descCount, descLongas = downloadDescricoes(modulo.PATH, aula.FULL_NAME, infoAula)

                        except KeyError:
                            pass

                        # Count Anexos
                        try:
                            attCount, anexosLongos = downloadAttachments(modulo.PATH, infoAula)
                        except KeyError:
                            pass

                        # Count Links Complementares
                        try:
                            linkCount, linksLongos = downloadLinks(modulo.PATH, aula.FULL_NAME, infoAula)
                        except KeyError:
                            pass

                    except (HTTPError, ConnectionError, Timeout, ChunkedEncodingError, ContentDecodingError):
                        hotmart._auth(USER_EMAIL, USER_PASS)
                        hotmart.setHeaders(infoCurso)
                        tryDL -= 1
                        continue
                    break
    except KeyError:
        print(f"\t{Colors.Red}Recurso sem módulos!{Colors.Reset}")

    with open(f"Cursos/{infoCurso.NOME}/info.txt", "w", encoding=ENCODING) as nfo:
        nfo.write(f"""Info sobre o rip do curso: {infoCurso.NOME} ({infoCurso._URL})
    Data do rip: {datetime.datetime.today().strftime('%d/%m/%Y')}
    Quantidade de recursos/erros (na run que completou):
        Quantidade de Módulos: {infoCurso.MODULOS.count};
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

    O script utilizado para download pode ser encontrado no seguinte link:
    https://github.com/katomaro/Hotmart-download-bot""")

    for f in glob.glob(f"{TEMP_FOLDER}/*"):
        try:
            os.remove(f)
        except:
            pass

    time.sleep(3)

    try:
        os.rmdir(TEMP_FOLDER)
    except:
        pass

    if not downloadAll:
        verCursos()

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

def criaCurso(nome):
    CURRENT_FOLDER = os.path.abspath(os.getcwd())
    BASE_PATH = criaSubDir(CURRENT_FOLDER, "Cursos")
    pathCurso = criaSubDir(BASE_PATH, nome)

    return pathCurso

def criaSubDir(parentDir, nome):
    dirPath = os.path.join(parentDir, nome)

    if not os.path.exists(dirPath):
        try:
            os.makedirs(dirPath)
        except:
            pass

    return dirPath

def limpaString(string):
    result = re.sub(r'[<>:!"/\\|?*]', '', string) \
        .strip() \
        .replace('.', '') \
        .replace("\t", "") \
        .replace("\n", "")

    return result

def criaArquivo(basePath, folder, prefix, name):
    fileDir = os.path.join(basePath, folder)
    filePath = os.path.join(fileDir, name)
    fileExtension = os.path.splitext(name)[1][1:].strip() 
    tempPath = os.path.join(basePath, prefix)

    if len(filePath) > 254:
        if not os.path.exists(tempPath):
            try:
                os.makedirs(tempPath)
            except:
                pass

        tempName = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        listPath = os.path.join(tempPath , "list.txt")

        try:
            with open(listPath, "a", encoding=ENCODING) as safelist:
                safelist.write(f"{tempName} = {folder}\n")
        except:
            pass

        filePath = os.path.join(tempPath , f"{tempName}.${fileExtension}")
    else:
        if not os.path.exists(fileDir):
            os.makedirs(fileDir)

    return filePath

def downloadDescricoes(pathModulo, nomeAula, infoAula):
    descCount = 0
    descLongas = 0

    if not 'content' in infoAula:
        return descCount, descLongas

    fileName = "desc.html"
    descPath = criaArquivo(pathModulo, nomeAula, "ed",  fileName)

    if not descPath.endswith(fileName):
        descLongas += 1

    if not os.path.isfile(descPath):
        try:
            with open(descPath, "w", encoding=ENCODING) as description:
                description.write(infoAula['content'])
                print(f"{Colors.Magenta}Descrição da aula salva!{Colors.Reset}")
                descCount += 1
        except:
            print(f"{Colors.Red}Erro ao salvar descrição da aula!{Colors.Reset}")

    return descCount, descLongas

def downloadLinks(pathModulo, nomeAula, infoAula):
    linkCount = 0
    linksLongos = 0

    if not 'complementaryReadings' in infoAula:
        return linkCount,linksLongos

    complimentaryReadings = infoAula['complementaryReadings']

    fileName = "links.txt"
    linksPath = criaArquivo(pathModulo, nomeAula, "el",  fileName)

    if not linksPath.endswith(fileName):
        linksLongos += 1

    if not os.path.isfile(f"{linksPath}"):
        print(f"{Colors.Magenta}Link complementar encontrado!{Colors.Reset}")

        try:
            for link in complimentaryReadings:
                with open(f"{linksPath}", "a", encoding=ENCODING) as linkz:
                    linkz.write(f"{link}\n")
        except:
            print(f"{Colors.Red}Erro ao salvar links complementares!{Colors.Reset}")

    else:
        print(f"{Colors.Green}Os links já estavam presentes!{Colors.Reset}")
    
    linkCount += 1

    return linkCount,linksLongos

def downloadAttachments(pathModulo, infoAula):
    anexosLongos = 0
    attCount = 0

    if not 'attachments' in infoAula:
        return attCount, anexosLongos

    for att in infoAula['attachments']:
        print(f"{Colors.Magenta}Tentando baixar o anexo: {Colors.Red}{att['fileName']}{Colors.Reset}")
        fileName = att['fileName']
        attachmentPath = criaArquivo(pathModulo, "Materiais", "et",  fileName)

        if not attachmentPath.endswith(fileName):
            anexosLongos += 1

        if not os.path.isfile(attachmentPath):
            while True:
                try:
                    anexo = hotmart.getAttachment(att)

                    with open(f"{attachmentPath}", 'wb') as ann:
                        ann.write(anexo.content)
                        print(f"{Colors.Magenta}Anexo baixado com sucesso!{Colors.Reset}")
                    break
                except:
                    print(f"{Colors.Red}Erro ao salvar anexo!{Colors.Reset}")

        attCount += 1

    return attCount, anexosLongos

def downloadVideos(tempFolder, pathModulo, nomeModulo, nomeAula, pathAula, infoAula):
    vidCount = 0
    videosLongos = 0
    segVideos = 0

    if not 'mediasSrc' in infoAula:
        return vidCount, videosLongos, segVideos

    for index, media in enumerate(infoAula['mediasSrc'], start=1):
        if media['mediaType'] != "VIDEO":
            continue

        print(f"\t{Colors.Magenta}Tentando baixar o vídeo {index}{Colors.Reset}")

        playerInfo = hotmart.getPlayerInfo(media)
        segVideos += playerInfo['mediaDuration']

        for asset in playerInfo['assets']:
            fileName = f"aula-{index}.mp4"
            videoPath = criaArquivo(pathModulo, nomeAula, "ev",fileName )

            if not videoPath.endswith(fileName):
                videosLongos += 1

            success = None

            if not os.path.isfile(videoPath):
                success = downloadVideoNativo(videoPath, tempFolder, nomeModulo, nomeAula, playerInfo['cloudFrontSignature'], asset)
            else:
                print("VIDEO JA EXISTE")
                success = True

            if success:
                vidCount += 1

    # tryDL = 0
    return vidCount, videosLongos, segVideos

def downloadVideoExterno(pathModulo, nomeCurso, nomeModulo, nomeAula, infoAula):
    try:
        fonteExterna = None
        videosLongos = 0
        videosInexistentes = 0
        vidCount = 0

        if not 'content' in infoAula:
            return vidCount, videosLongos, videosInexistentes

        content = BeautifulSoup(infoAula['content'], features="html.parser")
        iFrames = content.findAll("iframe")

        for index, iFrame in enumerate(iFrames, start=1):
            fileName = f"aula-{index}.mp4"
            videoPath = criaArquivo(pathModulo, nomeAula, "ev", fileName)

            if not videoPath.endswith(fileName):
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
                    # :( Ajuda noix  se possuir curso com esse player Telegram: @katomaro
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
                        errorPath = os.path.join(pathModulo, "erros.txt")

                        with open(errorPath, "a", encoding=ENCODING) as elog:
                            elog.write( f"{videoLink} - {nomeCurso}/{nomeModulo}/{nomeAula}")

                        videosInexistentes += 1
            else:
                vidCount += 1

                # tryDL = 0

    except KeyError:
        print(f"{Colors.Bold}{Colors.Red}Ué, erro ao salvar essa aula, pulada!{Colors.Reset} (verifique se ela tem vídeo desbloqueado na plataforma)")
        tryDL = 0

    return vidCount, videosLongos, videosInexistentes

def downloadVideoNativo(videoPath, tempFolder, nomeModulo, nomeAula, cloudFrontSignature, asset):
    try:
        if not 'url' in asset:
            return False

        videoData = hotmart.get(f"{asset['url']}?{cloudFrontSignature}")
        masterPlaylist = m3u8.loads(videoData.text)
        res = []
        highestQual = None

        for playlist in masterPlaylist.playlists:
            res.append(playlist.stream_info.resolution)

        res.sort(reverse=True)

        for playlist in masterPlaylist.playlists:
            if playlist.stream_info.resolution == res[0]:
                highestQual = playlist.uri

        if highestQual is not None:
            videoData = hotmart.get(f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual}?{cloudFrontSignature}")

            with open(f'{tempFolder}/dump.m3u8', 'w') as dump:
                dump.write(videoData.text)

            videoPlaylist = m3u8.loads(videoData.text)
            key = videoPlaylist.segments[0].key.uri
            totalSegmentos = videoPlaylist.segments[-1].uri.split(".")[0].split("-")[1]

            for segment in videoPlaylist.segments:
                print(f"\r\tBaixando o segmento {Colors.Blue}{segment.uri.split('.')[0].split('-')[1]}{Colors.Reset}/{Colors.Magenta}{totalSegmentos}{Colors.Reset}!", end="", flush=True)
                uri = segment.uri
                frag = hotmart.get(f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual.split('/')[0]}/{uri}?{cloudFrontSignature}")

                with open(f"{tempFolder}/" + uri, 'wb') as sfrag:
                    sfrag.write(frag.content)

            fragkey = hotmart.get(f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual.split('/')[0]}/{key}?{cloudFrontSignature}")

            with open(f"{tempFolder}/{key}", 'wb') as skey:
                skey.write(fragkey.content)

            print(f"\r\tSegmentos baixados, gerando video final! {Colors.Red}(dependendo da config do pc este passo pode demorar até 20 minutos!){Colors.Reset}", end="\n", flush=True)

            # TODO Implementar verificação de hardware acceleration
            # ffmpegcmd = f'ffmpeg -hide_banner -loglevel error -v quiet -stats -allowed_extensions ALL -hwaccel cuda -i {tempFolder}/dump.m3u8 -c:v h264_nvenc -n "{aulaPath}"'

            ffmpegcmd = f'ffmpeg -hide_banner -loglevel error -v quiet -stats -allowed_extensions ALL -i {tempFolder}/dump.m3u8 -n "{videoPath}"'

            if sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
                # MacOs specific procedures
                subprocess.run(ffmpegcmd, shell=True)
            elif sys.platform.startswith('win32'):
                # Windows specific procedures
                subprocess.run(ffmpegcmd)

                # TODO Implementar verificação de falha pelo FFMPEG
                # p = subprocess.run(ffmpegcmd)
                # if p.returncode != 0:
                #     pass

            print(f"Download da aula {Colors.Bold}{Colors.Magenta}{nomeModulo}/{nomeAula}{Colors.Reset} {Colors.Green}concluído{Colors.Reset}!")
            time.sleep(3)

            for ff in glob.glob(f"{tempFolder}/*"):
                os.remove(ff)
        else:
            print(f"{Colors.Red}{Colors.Bold}Algo deu errado ao baixar a aula, redefinindo conexão para tentar novamente!{Colors.Reset}")

            raise HTTPError
    except:
        return False

    return True

clearScreen()
verCursos()
