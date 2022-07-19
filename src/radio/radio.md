
# Title
Monk's Evil Radio

# Style
body {
  background-size: cover;
}

#player{
    position: relative;
    max-width: 700px;
    height: 500px;
    border: solid 1px gray;
}

img {
padding: 10px;
margin: 5px;
background-color: {color_accent_very_dark};
}

.scroll {
font-size: medium; 
line-height: 1.6;
}

# TODO
- [ ] rm bg, be chill with wavs

# HTML
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link rel="stylesheet" href="https://www.monksevillair.com/src/radio/css/AudioPlayer.css">
<!-- Audio player container-->
<div id='player'></div>

<!-- Audio player js begin-->
<script src="https://www.monksevillair.com/src/radio/js/AudioPlayer.js"></script>

<script>
      
                
      (async () => { 
        let mp3s = []; 
        let people = ["tilden","soda","criibaby","panda","casey","monk","zack","surfer-dave", "iocl"];
        
        const response = await fetch('https://api.github.com/repos/monksevillair/monksevillair.github.io/contents/src/radio/mp3/'); 
        const data = await response.json(); 
         // test image for web notifications
        var iconImage = null;
        
        for (let file of data) { 
          iconImage = null;
          if (file.name.indexOf(".mp3") !== -1) {
            for (let p of people) {
              if (file.name.indexOf(p) !== -1) {
                iconImage = "https://monksevillair.github.io/src/radio/mp3/pics/"+p+".jpg"
                console.log(iconImage);
              }
            }
            mp3s.push({'icon': iconImage, 'title': `${file.name}`, 'file': "https://github.com/monksevillair/monksevillair.github.io/blob/master/"+`${file.path}`+"?raw=true"});
          }
          //console.log(file);
          //htmlString += `${file.name}`; 
        } 
        //document.getElementsByClassName("substitute_div")[0].innerHTML = htmlString; 

       

        AP.init({
            container:'#player',//a string containing one CSS selector
            volume   : 0.7,
            autoPlay : true,
            notification: false,
            playList: mp3s.reverse()
        });
        
              })() 
</script>
<!-- Audio player js end-->
