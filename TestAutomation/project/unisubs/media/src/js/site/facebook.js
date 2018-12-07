
function statusChangeCallback(response) {
    if (response.status === 'connected') {
	if (document.getElementById('submit-proceed-to-create-facebook') != null) {
	    FB.api('/me?fields=first_name,last_name,email,picture', function(response) {
		console.log("Done");
		document.getElementById('id_avatar').value = response.picture.data.url;
		document.getElementById('id_first_name').value = response.first_name;
		document.getElementById('id_last_name').value = response.last_name;
		document.getElementById("submit-proceed-to-create-facebook").disabled = false;
	    });
	}
    }
}

window.fbAsyncInit = function() {
    if (document.getElementById("submit-proceed-to-create-facebook") != null) {
	document.getElementById("submit-proceed-to-create-facebook").disabled = true;
    }
    if (document.getElementById("facebook") != null) {
	document.getElementById("facebook").onclick = doLogin;
    }
    FB.init({
	appId      : document.facebook_app_public_id,
	cookie     : true,  // enable cookies to allow the server to access
        // the session
	xfbml      : true,  // parse social plugins on this page
	version    : 'v2.8' // use graph api version 2.8
    });
    FB.getLoginStatus(function(response) {
	statusChangeCallback(response);
    });
};

// Load the SDK asynchronously
(function(d, s, id) {
    var js, fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    js = d.createElement(s); js.id = id;
    js.src = "//connect.facebook.net/en_US/sdk.js";
    fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));

function doLogin() {
    FB.login(function(response) {
	  if (response.status === 'connected') {
	  FB.api('/me?fields=first_name,last_name,email,picture', function(response) {
	      window.location = document.facebook_login_confirm + response.email + "/";
	  });
      }
    }, {scope: 'public_profile,email'});
};
