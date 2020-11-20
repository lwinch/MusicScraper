import requests
import json
import wptools
import csv
import re


class WikiScraper:
    # genre_list = [
    #     "heavy metal", "thrash metal", "glam metal", "alternative metal", "progressive metal", "power metal",
    #     "symphonic metal", "neoclassical metal", "folk metal", "death metal", "black metal", "doom metal",
    #     "christian metal", "gothic metal", "groove metal", "industrial metal", "speed metal", "grunge",
    #     "crust punk", "kawaii metal", "latin metal", "metalcore", "grindcore", "avant-garde metal", "post-metal"]

    # FILL IN GENRES OF INTEREST HERE
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

    # todo: re categorize?
    #  groove metal part of thrash?
    #  gothic as doom metal?
    #  glam metal as heavy metal?
    #  combine post metal and avant-garde? or put avant garde in alternative metal?
    #  combine neoclassical and symphonic?
    #  combine speed and power? or put speed in traditional heavy metal?
    #  neue deutsche harte could be in thrash metal or industrial metal or alternative metal

    # todo: query all bands on spotify
    #    for each band, search for name, select first result, select see more get view count of top ten from table
    @staticmethod
    def build_wikipedia_search_url(query, start_index, size):
        url = 'https://en.wikipedia.org/w/api.php'

        params = {
               'action': 'query',
               'format': 'json',
               'list': 'search',
               'srsearch': query,
               'srnamespace': '0',
               'srlimit': str(size),
               'sroffset': str(start_index),
               'srinfo': 'totalhits'
        }
        return url, params

    def get_total_hits(self, query):
        wikipedia_url, params = self.build_wikipedia_search_url(query, 0, 1)
        r = requests.get(wikipedia_url, params=params)
        response_dict = json.loads(r.text)
        return response_dict.get('query').get('searchinfo').get('totalhits')

    def get_wikipedia_matches(self, query):
        print('getting matches for query: ', query)
        total_hits = self.get_total_hits(query)
        print(total_hits)

        article_matches = {}
        curr_start_index = 0
        has_next = True
        while has_next:
            print(curr_start_index)
            wikipedia_url, params = self.build_wikipedia_search_url(query, curr_start_index, 500)
            r = requests.get(wikipedia_url, params=params)
            response_dict = json.loads(r.text)
            if 'continue' in response_dict and 'sroffset' in response_dict['continue']:
                curr_start_index = response_dict['continue']['sroffset']
            else:
                has_next = False
            for result in response_dict['query']['search']:
                title = result['title']
                if '(' in title and ')' in title:
                    start = title.index('(')
                    end = title.index(')')
                    article_type = title[start:end]
                    if 'song' not in article_type and 'album' not in article_type:
                        article_matches[result['pageid']] = title
                else:
                    article_matches[result['pageid']] = title
            # time.sleep(random.randint(500, 1500) / 1000)
        return article_matches

    def get_wikipedia_matches_for_dict(self, genre_dict):
        # query all articles that contain each genre
        # get the list of pages that contain each genre
        article_matches = {}
        for query_parent, sub_query in genre_dict.items():
            curr_article_matches = self.get_wikipedia_matches('\"' + query_parent + '\" genre band')
            article_matches = {**article_matches, **curr_article_matches}
            for query in sub_query:
                print(len(article_matches))
                curr_article_matches = self.get_wikipedia_matches('\"' + query + '\" genre band')
                article_matches = {**article_matches, **curr_article_matches}
        return article_matches

    @staticmethod
    def get_band_wikidata_for_titles(title_list):
        title_str = '|'.join(title_list)
        params = {
            "action": "wbgetentities",
            "format": "json",
            "sites": "enwiki",
            "titles": title_str,
            "props": "descriptions|labels",
            "languages": "en"
        }
        wikidata_url = 'https://wikidata.org/w/api.php'
        r = requests.get(wikidata_url, params=params)
        response_dict = json.loads(r.text)

        results = []
        for (wikidata_id, fields), title in zip(response_dict['entities'].items(), title_list):
            if wikidata_id == '-1':
                results.append(['unknown', fields['title'], 'unknown', 'unknown'])
            else:
                try:
                    description = fields['descriptions']['en']['value']
                except KeyError:
                    description = 'unknown'
                try:
                    label = fields['labels']['en']['value']
                except KeyError:
                    label = 'unknown'

                not_band = ['album', 'song', 'single', 'compilation', 'discography', 'guitarist', 'video', 'drummer',
                            'vocalist', 'bassist']
                if description == 'unknown':
                    results.append([wikidata_id, title, label, description, 'unknown'])
                elif 'band' in description.lower() \
                        and not any(word in description.lower() for word in not_band) \
                        and 'EP' not in description:
                    results.append([wikidata_id, title, label, description, 'band'])
                else:
                    results.append([wikidata_id, title, label, description, 'NOT band'])
        return results

    def get_wikidata_for_all_titles(self, article_matches):
        name_list = list(article_matches.values())
        name_chunks = (name_list[pos:pos + 50] for pos in range(0, len(name_list), 50))
        all_wikidata = [['wikidata ID', 'title', 'label', 'description', 'is band']]
        progress = 0
        for chunk in name_chunks:
            print(progress)
            progress += len(chunk)
            try:
                wikidata = self.get_band_wikidata_for_titles(chunk)
                all_wikidata.extend(wikidata)
            except Exception:
                self.write_list(all_wikidata, '/home/lucas/Documents/full_data.csv')
                exit(0)
        return all_wikidata

    @staticmethod
    def parse_genre(genre_str):
        if genre_str is None:
            print('genre string None')
            return [None]
        split = re.split(r'\[|]|{|}|flatlist|hlist|, |\||\n\* ', genre_str)
        genres = []
        for string in split:
            if string != '':  # not in ['', '[', '{', 'flatlist', '|', '\\n* ', ']', '}']:
                genres.append(string)
        return genres

    @staticmethod
    def parse_years_active(years_active):
        try:
            return int(years_active[0:4])
        except (ValueError, TypeError):
            return years_active

    def get_infobox_for_band_article(self, title):
        so = wptools.page(title).get_parse()
        infobox = so.data['infobox']
        # print(infobox)
        if infobox is None:
            return None
        genre_str = infobox.get('genre') if infobox.get('genre') is not None else infobox.get('Genre')
        years_active = infobox.get('years_active')
        if genre_str is None and years_active is None:
            print('genre and years active is none for ', title)
            return None
        else:
            if '(' in title:
                short_title = title[:title.index('(')].strip()
            else:
                short_title = title
            genres = self.parse_genre(genre_str)
            years_active = self.parse_years_active(years_active)
            article_type = infobox.get('type')
            artist = infobox.get('artist')
            info = [title, short_title, article_type, artist, years_active] + genres
            return info

    def get_infobox_data(self, article_matches):
        print('getting info box data')
        infobox_data = [['article title', 'name', 'type', 'artist', 'first year active', 'genre1', 'genre2', 'genre3', 'genre4']]
        count = 0
        for title in article_matches.values():
            if count % 100 == 0:
                print('progress: ', count)
            count += 1
            # if it has a genre field,a save the band name, genre, active years, and other genres, and link to page
            infobox = self.get_infobox_for_band_article(title)
            if infobox is not None:
                infobox_data.append(infobox)
        return infobox_data

    def get_all_wikipedia_data(self):
        article_matches = self.get_wikipedia_matches_for_dict(self.sub_genre_map)
        self.write_dict(article_matches, '/home/lucas/Documents/full_matches.csv')
        # article_matches = self.read_dict('/home/lucas/Documents/full_matches.csv')
        print('results: ', len(article_matches))
        wikidata = self.get_wikidata_for_all_titles(article_matches)
        # infobox_data = self.get_infobox_data(article_matches)
        self.write_list(wikidata, '/home/lucas/Documents/full_data.csv')

    @staticmethod
    def read_dict(path):
        csv_dict = {}
        with open(path) as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                csv_dict[row[0]] = row[1]
        return csv_dict

    @staticmethod
    def write_dict(row_dict, path):
        with open(path, 'w') as output:
            writer = csv.writer(output)
            for key, value in row_dict.items():
                writer.writerow([key, value])

    @staticmethod
    def write_list(row_list, path):
        with open(path, 'w') as output:
            writer = csv.writer(output)
            for row in row_list:
                writer.writerow(row)

    @staticmethod
    def match_unmatched_data():
        path = '/home/lucas/Documents/unmatched_wikidata_hits.csv'
        wikidata = {}
        wikipedia_titles = []

        with open(path) as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                wikidata[row[0]] = row[2:]
                wikipedia_titles.append(row[1])
        out_path = '/home/lucas/Documents/rematched_wikidata_hits.csv'
        with open(out_path, 'w') as output:
            writer = csv.writer(output)
            writer.writerow(['wikidata id', 'name', 'label', 'band?', 'match?'])
            for wikidata_id, wikidata_fields in wikidata.items():
                label = wikidata_fields[0]
                match_found = False
                for title in wikipedia_titles:
                    if label in title:
                        writer.writerow([wikidata_id, title, *wikidata_fields])
                        match_found = True
                        wikipedia_titles.remove(title)
                        break
                if not match_found and label != 'unknown':
                    writer.writerow([wikidata_id, ' match not found', *wikidata_fields])

            for title in wikipedia_titles:
                writer.writerow([' unmatched', title, ' unmatched', ' unmatched', ' unmatched', ' unmatched'])


if __name__ == '__main__':
    ws = WikiScraper()
    ws.get_all_wikipedia_data()
    # ws.match_unmatched_data()
