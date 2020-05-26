// EDT: -04:00  EST: -05:00
var launchDate = new Date("2018-10-31T23:00:00-04:00");
// edit the above to change what the countdown timer is counting to

var x = setInterval(function() {
    var currentDate = new Date();
    var timeToLaunch = ( launchDate.getTime() - currentDate.getTime() ) / 1000; // in seconds

    var secondsToLaunch = Math.floor( (timeToLaunch % (60)) );
    var minutesToLaunch = Math.floor( (timeToLaunch % (60 * 60)) / (60) );
    var hoursToLaunch   = Math.floor( (timeToLaunch % (60 * 60 * 24)) / (60 * 60) );
    var daysToLaunch    = Math.floor( (timeToLaunch) / (60 * 60 * 24) );

    var spans = document.getElementById("countdown-text").childNodes;
    for (var i = 0; i < spans.length; i++) {
        if (spans[i].nodeName.toLowerCase() == "span") {
            spans[i].innerHTML =
                daysToLaunch + ":"
                + hoursToLaunch + ":"
                + minutesToLaunch + ":"
                + secondsToLaunch;
        }
    }

    if (!daysToLaunch && !hoursToLaunch && !minutesToLaunch && !secondsToLaunch) {
        clearInterval(x);
    }

}, 1000);
