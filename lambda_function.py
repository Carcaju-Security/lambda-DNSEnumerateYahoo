import re
import urllib.parse as urlparse
import requests
import json

base_url = "https://search.yahoo.com/search?p={query}&b={page_no}"


if 'session' not in globals():
    session = requests.Session()

timeout = 25
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Encoding': 'gzip',
}

def get_response(response):
    if response is None:
        return 0
    return response.text if hasattr(response, "text") else response.content


def send_req(query, page_no=1):

    url = base_url.format(query=query, page_no=page_no)
    try:
        resp = session.get(url, headers=headers, timeout=timeout)
    except Exception:
        resp = None
    return get_response(resp)

def check_response_errors(resp):
    if (type(resp) is str or type(resp) is unicode) and 'Our systems have detected unusual traffic' in resp:
        return False
    return True

def enumerate(domain):
    flag = True
    page_no = 0
    prev_links = []
    retries = 0
    subdomains = []
    MAX_DOMAINS = 10

    while flag:
        query = generate_query(domain, subdomains)
        # finding the number of subdomains found so far
        count = len(subdomains)

        # if they we reached the maximum number of subdomains in search query
        # then we should go over the pages
        if count >= MAX_DOMAINS:
            page_no += 10


        resp = send_req(query, page_no)
        # check if there is any error occured
        if not check_response_errors(resp):
            return subdomains
        links, subdomains = extract_domains(resp, domain, subdomains)

        # if the previous page hyperlinks was the similar to the current one, then maybe we have reached the last page
        if links == prev_links:
            retries += 1
            page_no += 10

    # make another retry maybe it isn't the last page
            if retries >= 3:
                return subdomains

        prev_links = links


    return subdomains


def extract_domains(resp, domain, subdomains):
    link_regx2 = re.compile('<span class=" fz-.*? fw-m fc-12th wr-bw.*?">(.*?)</span>')
    link_regx = re.compile('<span class="txt"><span class=" cite fw-xl fz-15px">(.*?)</span>')
    links_list = []
    try:
        links = link_regx.findall(resp)
        links2 = link_regx2.findall(resp)
        links_list = links + links2
        for link in links_list:
            link = re.sub(r"<(\/)?b>", "", link)
            if not link.startswith('http'):
                link = "http://" + link
            subdomain = urlparse.urlparse(link).netloc
            if not subdomain.endswith(domain):
                continue
            if subdomain and subdomain not in subdomains and subdomain != domain:
                subdomains.append(subdomain.strip())
    except Exception:
        pass

    return links_list, subdomains

def get_page(num):
    return num + 10

def generate_query(domain, subdomains):
    if subdomains:
        fmt = 'site:{domain} -domain:www.{domain} -domain:{found}'
        found = ' -domain:'.join(subdomains[:77])
        query = fmt.format(domain=domain, found=found)
    else:
        query = "site:{domain}".format(domain=domain)
    return query


def lambda_handler(event, context):

    domain = event['domain']
    domains = enumerate(domain)
    print(domains)
    return {
        'statusCode': 200,
        'body': json.dumps(domains)
    }
