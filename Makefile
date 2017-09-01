PYTHON=`which python`
DESTDIR=/
PROJECT=nmos-connection

deb:

	make deb -C nmos-connection/
	make deb -C reverse-proxy/
clean:
	make clean -C nmos-connection/
	make clean -C reverse-proxy/
	rm *.tar.gz *.dsc *.deb *.build *.changes
