HTTP Cache server
=========

what is this?
-------------

This is a script that act as proxy between your web browser and some domaines of your choice.
Whenever your webbrowser request a page in one of these domains the script download the page, cache it and then return it to your browser.
future requests to the same page will be returned from the offline cache.

Use cases for this script
-------------------------

- conserve bandwidth when frequently accessing a site with a static or semi-static content (ex: documentations of certain version of a software).
- access the previously visited pages of a selected domained offline.
- if you are web developer who want to develop sites offline but unable to because your site require files hosted for example on ajax.googleapis.com

How to use?
--------------------------

1. Generate a certifcate file  `openssl req -new -x509 -nodes -out cert.pem -keyout cert.pem` 
2. Decide what domains you want to cache. lets use _ajax.googleapis.com_ as an example.
3. Add the following to your /etc/hosts : `127.0.0.2   ajax.googleapis.com`
4. Try to access _http://ajax.googleapis.com/ajax/libs/jquery/2.0.3/jquery.min.js_ you should get an error
5. Create a cache directory, for example `mkdir ~/web_cache`
6. Run the script __as root__, `python3 cache_server.py ~/web_cache cert.pem`
7. Now visit _http://ajax.googleapis.com/ajax/libs/jquery/2.0.3/jquery.min.js_ again, it should work
8. Visit it again but use __https__ instead of __http__, naturally you will get certeficate error. say you trust this certeficate.
9. Done! Now you can access this url offline.

__Note__: Some webbrowsers don't bother making http requests when it detect you have no internet connection.

__For adding more domains___:
1. Add the following to your /etc/hosts : `127.0.0.2   <domain name>`
2. If you want to support https you must visit any url in this domain and tell the browser to trust the certifcate we generated earlier. 
3. Done

__Note__: instead of doing

    127.0.0.2  example.com
    127.0.0.2  sub.example2.com

You can do

    127.0.0.2  example.com sub.example2.com

Known limitations
---------------------------
* The script has to run on port 80, if you already use this port for apache make sure it only listen to 127.0.0.1:80 and not *:80
* The script support https requests but your webbrowser will complain about invalid certeficate, this is normal because the script is acting as a man in the middle between you and the site you are visiting. in firefox you can say I understand the risks and add an exception
