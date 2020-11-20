import requests
import json
import time
# import random
import pandas as pd
import fold_to_ascii


# todo:
#  query artist at https://api.spotify.com/v1/search?q=Metallica&type=artist&limit=1
#  get genres, popularity and artist id for the response
#  get all albums for artist at https://api.spotify.com/v1/artists/1vCWHaC5f2uS3yhpwWbIA6/
#  albums?include_groups=album&market=US&limit=50
#  loop through albums and find oldest album and save year

class SpotifyScraper:

    sub_genre_map = {
        "alternative metal": ["funk metal", "nu metal", "rap metal", "trap metal"],
        "avante-garde metal": ["avant-metal", "experimental metal"],
        "black metal": [
            "ambient black metal", "folk black metal", "industrial black metal", "symphonic black metal",
            "post-black metal", "blackgaze", "psychedelic black metal",
            "black \'n\' roll", "black doom", "depressive suicidal black metal", "blackened crust",
            "blackened death doom", "blackened death metal", "melodic black-death", "war metal",
            "national socialist black metal", "anarchist black metal", "red black metal",
            "blackened grindcore", "blackened thrash metal", "blackened heavy metal",
            "Symphonic black metal", "blackened screamo", "viking metal", "pagan metal"],
        "christian metal": ["white metal", "jesus metal", "heavenly metal", "unblack metal"],
        "crust punk": ["crust", "stenchcore", "crustcore", "blackened crust", "crack rock steady"],
        "death metal": [
            "brutal death metal", "industrial death metal", "melodic death metal", "slam death metal",
            "symphonic death metal", "technical death metal",
            "blackened death-doom", "blackened death metal", "melodic black-death", "war metal", "death-doom",
            "deathcore", "deathgrind", "deathrash", "death \'n\' roll", "goregrind", "pornogrind"],
        "doom metal": [
            "epic doom", "traditional doom", "black-doom", "depressive suicidal black metal",
            "blackened death-doom", "death-doom", "drone metal", "funeral doom", "gothic doom", "progressive doom",
            "sludge metal", "stoner metal"],
        "folk metal": ["celtic metal", "pirate metal", "pagan metal", "viking metal", "medieval metal",
                       "oriental metal"],
        "glam metal": ["hair metal", "pop metal"],
        "gothic metal": ["goth metal", "Symphonic gothic metal"],
        "grindcore": ["deathgrind", "goregrind", "pornogrind", "electrogrind"],
        "grunge": ["post-grunge"],
        "industrial metal": ["industrial death metal", "industrial black metal"],
        "kawaii metal": ["idol metal", "cute metal", "kawaiicore"],
        "latin metal": [],
        "metalcore": [
            "metallic hardcore", "melodic metalcore", "deathcore", "easycore", "progressive metalcore", "mathcore",
            "electronicore", "nu metalcore"],
        "neoclassical metal": [],
        "neue deutsche harte": ["new german hardness", "NDH", "dance metal", "tanzmetall"],
        "post-metal": ["metalgaze", "blackgaze"],
        "power metal": ["symphonic power metal"],
        "progressive metal": [
            "prog metal", "djent", "space metal", "progressive metalcore", "progressive doom"],
        "speed metal": [],
        "symphonic metal": [
            "opera metal", "operatic metal", "symphonic black metal", "symphonic death metal", "symphonic gothic metal",
            "symphonic power metal"],
        "thrash metal": [
            "blackened thrash metal", "crossover thrash", "deathrash", "groove metal", "teutonic thrash metal"],
        "heavy metal": ["new wave of traditional heavy metal"]
    }

    @staticmethod
    def read_band_list(file_name, has_index) -> pd.DataFrame:
        if has_index:
            band_df = pd.read_csv(file_name, header=0, index_col=0)
        else:
            band_df = pd.read_csv(file_name, header=0)
        print(band_df.head(5))
        return band_df

    def get_response(self, url, params, headers):
        try:
            response = requests.get(url=url, params=params, headers=headers, timeout=10)
        except Exception as e:
            print('REQUEST FAILED:', e)
            return self.get_response(url, params, headers)
        band_json = json.loads(response.text)
        if band_json is None:
            print('no response')
            return None
        elif 'error' in band_json and band_json['error']['status'] == 429:
            wait_time = int(response.headers.get('retry-after'))
            print('waiting:', wait_time)
            time.sleep(wait_time)
            return self.get_response(url, params, headers)
        elif 'error' in band_json:  # and band_json['error']['status'] == '401'
            print(band_json)
            message = band_json['error']['message']
            print('error: ', message)
            return None
        return band_json

    def get_band_id(self, band_id, o_auth):
        query_url = 'https://api.spotify.com/v1/artists/' + band_id
        params = {}
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + o_auth}
        band_json = self.get_response(query_url, params, headers)
        if band_json is None:
            return {
                'name': 'not found',
                'id': 'not found',
                'genres': [],
                'popularity': -1
            }
        return band_json

    def query_band(self, band_name, o_auth):
        query_url = 'https://api.spotify.com/v1/search'
        params = {
            'q': band_name,
            'type': 'artist',
            'limit': 10
        }
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + o_auth}
        band_json = self.get_response(query_url, params, headers)
        if band_json is None:
            return None
        try:
            # match if the artist name is exactly the same and the genre is metal.
            # if no metal bands exist return the best non metal band
            band_info_non_metal = None
            band_info = None
            for item in band_json.get('artists').get('items'):
                if fold_to_ascii.fold(band_name.lower()) == fold_to_ascii.fold(item.get('name').lower()):
                    contains_metal = False
                    for genre in item.get('genres'):
                        if 'metal' in genre:
                            contains_metal = True
                            break
                    if contains_metal:
                        band_info = item
                    elif band_info_non_metal is None:
                        band_info_non_metal = item
                if band_info is not None:
                    break
            if band_info is None and band_info_non_metal is not None:
                band_info = band_info_non_metal
        except IndexError:
            band_info = None
        if band_info is None:
            band_info = {
                'name': 'not found',
                'id': 'not found',
                'genres': [],
                'popularity': -1
            }
        print(band_info.get('name'), band_info.get('id'), band_info.get('genres'), band_info.get('popularity'))
        return band_info

    def query_band_first_album(self, band_info, o_auth):
        artist_id = band_info.get('id')
        if artist_id == 'not found':
            return -1
        query_url = 'https://api.spotify.com/v1/artists/' + artist_id + '/albums'
        params = {
            'include_groups': 'album',
            'market': 'US',
            'limit': 50
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + o_auth
        }
        response = self.get_response(query_url, params, headers)
        if response is None:
            return None
        albums_info = response.get('items')
        oldest_album = 9999
        for album_info in albums_info:
            album_year = int(album_info.get('release_date')[0:4])
            if album_year < oldest_album:
                oldest_album = album_year
        return oldest_album

    @staticmethod
    def df_add_column(dataframe, name, col_data):
        max_len = len(dataframe)
        if len(col_data) != max_len:
            col_data.extend([''] * (max_len - len(col_data)))
        dataframe[name] = col_data

    def extract_genres(self, genres):
        genre_set = set()

        for genre in genres:
            for sub_genre, syn in self.sub_genre_map.items():
                if genre == sub_genre or genre in syn:
                    genre_set.add(sub_genre)
        return genre_set

    def query_all_bands(self, file_name, has_index, o_auth, offset):
        band_df = self.read_band_list(file_name, has_index)

        if 'spotify name' not in band_df.columns:
            band_df['spotify name'] = ''
            band_df['spotify id'] = ''
            band_df['spotify genres'] = ''
            band_df['spotify extracted genres'] = ''
            band_df['spotify popularity'] = ''
            band_df['spotify first album year'] = ''
        for row in band_df.iloc[offset:].itertuples():
            band_info = self.query_band(row[3], o_auth)
            if band_info is None:
                break
            year = self.query_band_first_album(band_info, o_auth)
            if year is None:
                break
            band_df.loc[row.Index, 'spotify name'] = band_info.get('name')
            band_df.loc[row.Index, 'spotify id'] = band_info.get('id')
            band_df.loc[row.Index, 'spotify popularity'] = band_info.get('popularity')
            band_df.loc[row.Index, 'spotify first album year'] = year

            genres = band_info.get('genres')
            band_df.loc[row.Index, 'spotify genres'] = str(genres)
            genre_set = self.extract_genres(genres)
            band_df.loc[row.Index, 'spotify extracted genres'] = str(list(genre_set))
        return band_df

    def get_spotify_ids(self, file_name, has_index, o_auth):
        band_df = self.read_band_list(file_name, has_index)
        for index, row in band_df.iterrows():
            band_id = row['spotify id']
            if band_id != 'not found' and row['spotify name'] == 'not found':
                band_info = self.get_band_id(band_id, o_auth)
                if band_info is None:
                    break
                year = self.query_band_first_album(band_info, o_auth)
                if year is None:
                    break
                band_df.loc[index, 'spotify name'] = band_info.get('name')
                band_df.loc[index, 'spotify id'] = band_info.get('id')
                band_df.loc[index, 'spotify popularity'] = band_info.get('popularity')
                band_df.loc[index, 'spotify first album year'] = year

                genres = band_info.get('genres')
                band_df.loc[index, 'spotify genres'] = str(genres)
                genre_set = self.extract_genres(genres)
                band_df.loc[index, 'spotify extracted genres'] = str(list(genre_set))
        return band_df


if __name__ == '__main__':
    # FILL IN TOKEN HERE
    o_a = ''
    # f_n = '/home/lucas/Documents/wikidata_band_hits.csv'
    # f_n = '/home/lucas/Documents/unknown_wikipedia_hits.csv'
    # f_n = '/home/lucas/Documents/spotify_wikidata_not_found.csv'
    f_n = '/home/lucas/Documents/spotify_wikidata_unknown_not_found.csv'

    # out_file = '/home/lucas/Documents/spotify_wikidata_band_out.csv'
    # out_file = '/home/lucas/Documents/spotify_wikidata_unknown_out.csv'
    # out_file = '/home/lucas/Documents/spotify_wikidata_not_found_out.csv'
    out_file = '/home/lucas/Documents/spotify_wikidata_unknown_not_found_out.csv'
    scraper = SpotifyScraper()

    # df = scraper.query_all_bands(f_n, False, o_a, 0)
    df = scraper.get_spotify_ids(f_n, True, o_a)
    df.to_csv(out_file)
