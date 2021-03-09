import xlrd
from elasticsearch import Elasticsearch
# PS: The names are not the same 100% so we can't just use WooCommerce API to find by name
# Install the following
# pip install elasticsearch
# pip install xlrd
# pip install WooCommerce

# you need also cloud.elastic.co search key and your woocommerce rest api auth keys

#Connecting to remote elasticsearch engine
es = Elasticsearch(
    [ 'https://29b7e8b2469548f0a98d4aa3b0eddc7b.eastus2.azure.elastic-cloud.com',],
    http_auth=('elastic', 
    'nH9N2IOSzbrFAzHdt5bGxKKr' # your cloud.elastic.co search key , this one won't work
    ),
    scheme="https",
    port=9243,
)
#Loading your data from file and indexing them to ES engine
# the file that holds all your new prices xlsx
# here we index it to elastic search engine  
loc = ("./new_prices_products.xls") 
wb = xlrd.open_workbook(loc)
sheet = wb.sheet_by_index(0)
def setting_up_es():
    for x in range(0,sheet.nrows):
        name = sheet.cell_value(x, 0)
        price = sheet.cell_value(x, 1)
        doc = {
            'name': name,
            'price': price,
        }
        res = es.index(index="products", id=x, body=doc)
        print(res['result'])

# ES search for name  
# helper function to get the price of a product from elastic search engine
def get_new_name_and_price(name):
    res = es.search(index="products", body={'query': {'match': {'name': name}}})
    if len(res['hits']['hits'])>0:
        return res['hits']['hits'][0]['_source']['name'],res['hits']['hits'][0]['_source']['price'],res['hits']['hits'][0]['_score']
    else:
        return None,None,0

from woocommerce import API
def main():
    #connecting to your woocommerce REST API
    wcapi = API(
        url="https://your_wordpress_domain.com",
        consumer_key="ck_5e55eb1f8b3po06e47f16bdd733980dc9196a7a6",# your WooCommerce API key this one won't work
        consumer_secret="cs_4aa7999999262fa19224451945ed7f58fa6ac494",# your WooCommerce API secret this one won't work
        wp_api=True,
        query_string_auth=True,
        version="wc/v3"
    )
    # for performance we load all the products in a list
    products  = []
    for x in range(4):
        p = wcapi.get(f"products?per_page=300&offset={300*x}").json()
        products.extend(p)
    # We in each product and use the search engine to find if any updates in the prices
    for x,product in enumerate(products):
        name = product['name']
        price = product['regular_price']
        n_name, n_price, score = get_new_name_and_price(name)
        try:
            score = int(score)
        except:
            score = 0
        if n_name == None or score < 13:
            wcapi.delete(f"products/{product['id']}", params={"force": True}).json()
            print(f'{x} / {score} - Deleted {name} ~ {n_name}')
            if score < 13 and n_name != None: 
                data = {
                    "regular_price": str(n_price),
                    "name": n_name,
                    "status": "publish",
                }
                wcapi.post(f"products", data).json()
                print(f'Created new version of {n_name}')
        else:
            try:
                if float(price) != float(n_price):
                    data = {
                        "regular_price": str(n_price),
                        "name": n_name,
                        "status": "publish",
                    }
                    wcapi.put(f"products/{product['id']}", data).json()
                    print(f'{x} / {score} - Updated {name} ~ {price}')
                    print(f'{x} / {score} - Updated {n_name} ~ {n_price}')
                else:
                    print('Pass')
            except Exception as e:
                print(e)