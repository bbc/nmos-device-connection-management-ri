Vagrant.configure("2") do |config|
  puts "Configuring proxy settings..."
  if Vagrant.has_plugin?("vagrant-proxyconf")
    puts "Found vagrant-proxyconf plugin - Now checking envinronent variables..."
    if ENV["http_proxy"]
      puts "http_proxy is set to: " + ENV["http_proxy"]
      config.proxy.http     = ENV["http_proxy"]
      config.apt_proxy.http = ENV["http_proxy"]
    end
    if ENV["https_proxy"]
      puts "https_proxy is set to: " + ENV["https_proxy"]
      config.proxy.https    = ENV["https_proxy"]
      config.apt_proxy.https = ENV["https_proxy"]
    end
    if ENV["no_proxy"]
      puts "no_proxy paths set to: " + ENV["no_proxy"]
      config.proxy.no_proxy = ENV["no_proxy"]
    end
  end

  config.vm.define "connection" do |connection|
 	connection.vm.box = "bento/ubuntu-16.04"
	connection.vm.hostname = "connection"
  	connection.vm.provider "virtualbox" do |vb|
      		vb.gui = false
  	end

  	connection.vm.network "forwarded_port", type: "dhcp", guest: 80, host: 8080
        connection.vm.network "forwarded_port", type: "dhcp", guest: 8856, host: 8856
  	connection.vm.network "forwarded_port", type: "dhcp", guest: 8858, host: 8858
  	connection.vm.network "forwarded_port", type: "dhcp", guest: 8860, host: 8860
  	connection.vm.provision :shell, path: "provision_node.sh"
  end
end

