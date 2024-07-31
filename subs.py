# Created By Gullith
import os
import struct
import requests
from tabulate import tabulate

# Defina as extensões de vídeo que deseja procurar
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']

def calculate_hash(name):
    """Calculate the OpenSubtitles hash of a movie file."""
    try:
        longlongformat = '<q'  # little-endian long long
        bytesize = struct.calcsize(longlongformat)

        with open(name, "rb") as f:
            filesize = os.path.getsize(name)
            hash_value = filesize

            if filesize < 65536 * 2:
                raise ValueError("File size too small for hashing")

            for _ in range(65536 // bytesize):
                buffer = f.read(bytesize)
                (l_value,) = struct.unpack(longlongformat, buffer)
                hash_value += l_value
                hash_value &= 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

            f.seek(max(0, filesize - 65536), 0)
            for _ in range(65536 // bytesize):
                buffer = f.read(bytesize)
                (l_value,) = struct.unpack(longlongformat, buffer)
                hash_value += l_value
                hash_value &= 0xFFFFFFFFFFFFFFFF

        returnedhash = "%016x" % hash_value
        return returnedhash

    except IOError:
        print("File not accessible")
        return None

def find_video_files(directory):
    """Encontre todos os arquivos de vídeo no diretório especificado."""
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                video_files.append(os.path.join(root, file))
    return video_files

API_URL = 'https://rest.opensubtitles.org/search'
HEADERS = {'User-Agent': 'TemporaryUserAgent'}  # Substitua com um User-Agent válido

class OpenSubtitlesClient:
    def __init__(self, api_url=API_URL, headers=HEADERS):
        self.api_url = api_url
        self.headers = headers

    def search_subtitles_by_movie_name(self, movie_name):
        """Search for subtitles by movie name."""
        url = f'{self.api_url}/query-{movie_name}/sublanguageid-pob'
        return self._make_request(url)
    
    def search_subtitles_by_hash(self, movie_hash):
        """Search for subtitles by movie hash."""
        url = f'{self.api_url}/moviebytesize-0/moviehash-{movie_hash}/sublanguageid-pob'
        return self._make_request(url)

    def download_subtitle(self, subtitle):
        """Download the chosen subtitle."""
        download_link = subtitle['SubDownloadLink']
        file_name = subtitle['SubFileName']
        try:
            response = requests.get(download_link)
            response.raise_for_status()  # Will raise HTTPError for bad responses
            with open(file_name, 'wb') as f:
                f.write(response.content)
            print(f"Legenda baixada: {file_name}")
        except requests.exceptions.RequestException as e:
            print(f"Erro no download: {e}")

    def _make_request(self, url):
        """Make a request to the API and return the response data."""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Will raise HTTPError for bad responses
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro na busca: {e}")
            return None

def display_subtitles(subtitles):
    """Display the subtitles sorted by rating."""
    # Ordena as legendas pela pontuação (assumindo que o campo é 'SubRating')
    sorted_subtitles = sorted(subtitles, key=lambda x: x.get('SubRating', 0), reverse=True)
    table_data = [
        [i, subtitle['SubFileName'], subtitle['LanguageName'], subtitle.get('SubRating', 'N/A')]
        for i, subtitle in enumerate(sorted_subtitles, 1)
    ]
    headers = ["#", "File Name", "Language", "Rating"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    return sorted_subtitles

def get_user_choice(num_options):
    """Get a valid choice from the user."""
    while True:
        try:
            choice = int(input(f"Escolha o número (0-{num_options}): "))
            if 0 <= choice <= num_options:
                return choice
            else:
                print(f"Escolha inválida. Digite um número entre 0 e {num_options}.")
        except ValueError:
            print("Entrada inválida. Por favor, digite um número.")

def choose_video_file(video_files):
    """Display video files and let the user choose one."""
    if not video_files:
        print("Nenhum arquivo de vídeo encontrado no diretório atual.")
        return None
    
    print("Arquivos de vídeo encontrados:")
    for i, video_file in enumerate(video_files, 1):
        print(f"{i}. {video_file}")
    print("0. Cancelar")

    while True:
        try:
            choice = int(input(f"Escolha o número do arquivo de vídeo para usar (0-{len(video_files)}): "))
            if 0 <= choice <= len(video_files):
                if choice == 0:
                    return None
                return video_files[choice - 1]
            else:
                print(f"Escolha inválida. Digite um número entre 0 e {len(video_files)}.")
        except ValueError:
            print("Entrada inválida. Por favor, digite um número.")

def main():
    client = OpenSubtitlesClient()

    search_option = input("Escolha a opção de pesquisa: (1) Nome do filme (2) Hash do filme: ").strip()
    if search_option == '1':
        name_option = input("Escolha a opção de nome: (1) Digitar nome do filme (2) Escolher nome do arquivo de vídeo: ").strip()
        if name_option == '1':
            query = input("Digite o nome do filme: ").strip()
            if not query:
                print("O nome do filme não pode ser vazio.")
                return

            results = client.search_subtitles_by_movie_name(query)
        elif name_option == '2':
            current_directory = os.getcwd()
            video_files = find_video_files(current_directory)
            chosen_file = choose_video_file(video_files)
            
            if not chosen_file:
                print("Nenhum arquivo de vídeo selecionado.")
                return

            query = os.path.splitext(os.path.basename(chosen_file))[0]
            results = client.search_subtitles_by_movie_name(query)
        else:
            print("Opção de nome inválida.")
            return
    
    elif search_option == '2':
        current_directory = os.getcwd()
        video_files = find_video_files(current_directory)
        chosen_file = choose_video_file(video_files)
        
        if not chosen_file:
            print("Nenhum arquivo de vídeo selecionado.")
            return

        movie_hash = calculate_hash(chosen_file)
        if not movie_hash:
            print("Não foi possível calcular o hash do arquivo.")
            return

        results = client.search_subtitles_by_hash(movie_hash)
    
    else:
        print("Opção de pesquisa inválida.")
        return

    if results:
        sorted_results = display_subtitles(results)

        while True:
            choice = get_user_choice(len(sorted_results))
            if choice == 0:
                print("Operação cancelada.")
                break
            chosen_subtitle = sorted_results[choice - 1]
            client.download_subtitle(chosen_subtitle)

            # Pergunta ao usuário se deseja continuar baixando
            continue_choice = input("Deseja continuar baixando? (s/n): ").strip().lower()
            if continue_choice != 's':
                break
    else:
        print("Nenhuma legenda encontrada.")

if __name__ == "__main__":
    main()
