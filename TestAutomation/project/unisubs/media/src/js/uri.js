var AmaraURI = function (url){
    var parserEl = document.createElement('a');
    parserEl.href = url;

    this.domainEquals = function(domain){
        return parserEl.hostname == domain;
    }
    this.domainContains = function(domain){
        return parserEl.hostname.indexOf(domain) > -1;
    }
    this.fileExtension = function(){
        var dotPlacement = parserEl.pathname.lastIndexOf(".");
        if ( dotPlacement == "-1"){
            return null;
        }
        // FIXME:  split paths
        return parserEl.pathname.substring(dotPlacement + 1);
    }

}