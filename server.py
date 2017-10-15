from http.server import BaseHTTPRequestHandler, HTTPServer
import crawler
import pprint
import math
from bson.son import SON

class SimpleHandler(BaseHTTPRequestHandler):
    SEARCH_PARAMS = ['Country', 'Type', 'Released', 'Status', 'Tagges as', 'Genre']
    NUM_RESULT_PER_PAGE = 10

    db_collection_ = crawler.get_db_collection()

    def do_GET(self):
        self.send_response(200)

        self.send_header('Content-type', 'text/html')
        self.end_headers()

        all_videos = self.db_collection_.find()
        number_of_videos = all_videos.count()

        print('pass query', self.path, self.path.find('?'))

        print('generate filters')

        params = self.get_params()

        result = self.do_search(params)

        filters_html = self.generate_filters(params, result)

        result_html = self.render_result(result)

        print('generate message')

        message = """<!DOCTYPE html>
        <html>
            <head>
                <title>Drama List</title>
            </head>
            <body>
                <h1>Easier way to find Asian Dramas</h1>
                <hr/>
                <p>There are currently: %d movies / dramas. </p>
                %s
                <hr/>
                <h2>Search Result</h2>
                %s
            </body>
        </html>
        """ % (number_of_videos, filters_html, result_html)

        print('output header')

        print(self.requestline)
        print(self.path)
        print(self.headers)

        print('output result')


        self.wfile.write(bytes(message, 'utf8'))

        self.wfile.flush()

        print('returning')

        return


    def get_list_of(self, field):
        options = [(a['_id'], a['count']) for a in self.db_collection_.aggregate([
            {"$unwind": "$" + field},
            {'$group': {"_id": "$" + field, "count": {"$sum": 1}}}])]
        return sorted(options, key=lambda x: x[0])


    def render_pagination(self, params, result):
        if result and result.count() > self.NUM_RESULT_PER_PAGE:
            total_pages = int(math.ceil(result.count() / self.NUM_RESULT_PER_PAGE))
            pages = range(0, total_pages+1)
            cur_page = int(params['Page']) if 'Page' in params.keys() else 0

            option_html= ''.join('<option value="%d" %s> %d </option>' % (p, 'selected' if p == cur_page else'', p+1) for p in pages)
            return '<div><label>Page:</label><select name="Page"> %s </select></div>' % option_html
        else:
            return ''


    def generate_filters(self, params, result):
        filters_html = ''
        for f in self.SEARCH_PARAMS:
            s_option = params[f] if f in params.keys() else None

            options = self.get_list_of(f)
            option_html = '<option value="-" %s> All </option>' % ('selected' if not s_option else '')
            option_html += ''.join('<option value="%s" %s> %s - %d </option>' %
                                  (v[0], ('selected' if s_option and v[0] == s_option else ''), v[0], v[1]) for v in options)
            select_html = '<select name="%s"> %s </select>' % (f, option_html)
            filters_html += '<div> <label>%s</label> %s </div>'%(f, select_html)

        filters_html += self.render_pagination(params, result)

        title_text = params['TitleText'] if 'TitleText' in params.keys() else ''
        print('TitleText:', title_text)

        form_html = """
        <form action="" method="get">
            %s
            <div><label>Search Title:</label><input type="text" name="TitleText" value="%s"></input></div>
            <input type="submit" value="Search"></input>
        </form>
        """ %(filters_html, title_text)

        return form_html

    def do_search(self, params):
        # filter out non search parameters
        search_params = {}
        for p in self.SEARCH_PARAMS:
            if p in params.keys():
                search_params[p] = params[p]

        cur_page = int(params['Page']) if 'Page' in params else 0
        start = cur_page * self.NUM_RESULT_PER_PAGE
        end = (cur_page + 1) * self.NUM_RESULT_PER_PAGE

        title_text = params['TitleText'] if 'TitleText' in params.keys() else ''
        if title_text != '':
            search_params['$text'] = {'$search': title_text, '$caseSensitive': False}
            self.db_collection_.create_index([('Title', 'text')])

        result = self.db_collection_.find(search_params)[start:end]

        return result

    def render_result(self, result):
        result_html = '<p>Total number of videos found:  %d</p>' % (result.count())
        for r in result:
            episodes_html = ''
            for episode in sorted(r['Episodes'],key=lambda x: x['Name']):
                link = episode['VideoUrl'] if 'VideoUrl' in episode.keys() else episode['Url']
                episodes_html += '<tr><td><a href="%s" target="_blank">%s</td></tr>' % (link, episode['Name'])

            result_html += """
            <div>
            <table><tr><td>
                <a href="%s" target="_blank" >
                <img src="%s" width="300px"/>
                </a>
                </td>
                <td>
            <table>
                <tr><td>Title:</td><td>%s</td></tr>
                <tr><td>Country:</td><td>%s</td></tr>
                <tr><td>Released:</td><td>%s</td></tr>
                <tr><td>Genre:</td><td>%s</td></tr>
                <tr><td>Cast:</td><td>%s</td></tr>
                <tr><td>Type:</td><td>%s</td></tr>
                <tr><td>Status:</td><td>%s</td></tr>
                %s
            </table>
            </td>
            </tr></table>
            </div>
            <hr/>
            """ % ('https://gogodramaonline.com/info/' + r['Title'].replace(' ', '-'),
                   r['ImageUrl'], r['Title'], r['Country'], r['Released'], r['Genre'],
                   r['Tagges as'], r['Type'], r['Status'], episodes_html)

        return result_html

    def get_params(self):
        if self.path.find('?') == -1:
            return {}

        query = self.path.split('?')[1] if self.path.find('?') != -1 else ''
        query_kv = [[v.replace('+', ' ') for v in p.split('=', 1)] for p in query.split('&') if p.split('=', 1)[1] != '-']
        params = dict(query_kv) if len(query_kv) > 0 and query_kv != [['']] else {}

        print('Search Param:', params)

        return params



if __name__ == '__main__':
    port = 8080
    print('starting server localhost:', port)
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()