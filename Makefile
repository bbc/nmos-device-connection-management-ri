PYTHON=`which python`
DESTDIR=/
PROJECT=nmos-connection

deb:
	make deb -C nmos-connection/
clean:
	make clean -C nmos-connection/
	rm *.tar.gz *.dsc *.deb *.build *.changes
