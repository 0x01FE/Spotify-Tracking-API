
# Top Artists
curl -H "user: 1" 127.0.0.1:5000/top/artists | python3 -m json.tool

# Top Albums
curl -H "user: 1" 127.0.0.1:5000/top/albums | python3 -m json.tool

