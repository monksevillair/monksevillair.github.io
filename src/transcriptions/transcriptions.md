
# Title
Transcriptions

# Style

# TODO
- [ ] Fix formatting, make specific blog parser

# HTML
## Transcriptions
<script>
      (async () => {
        const response = await fetch('https://api.github.com/repos/monksevillair/monksevillair.github.io/contents/src/transcriptions/');
        const data = await response.json();
        let htmlString = '';
        for (let file of data) {
          htmlString += `<a href="https://www.monksevillair.com/src/transcriptions/${file.name}">${file.name}</a></br>`;
        }
        htmlString += '';
        <!--document.getElementsByTagName('body')[0].innerHTML = htmlString;-->
		document.getElementsByClassName("substitute_div")[0].innerHTML = htmlString;

      })()
</script>
</br>
<div class="substitute_div"> </div> 

<!--[Frank Zappa - Montana (Vox Solo)](../src/transcriptions/Montana_Marimba_Vox_Solo.pdf)  
[Wayne Shorter - Black Nile](../src/transcriptions/Black_Nile_Wayne_Shorter.pdf)  
[Monk - Africa](../src/transcriptions/Africa.pdf)  
[Monk - And it Grows](../src/transcriptions/and_it_grows.pdf)  
[Monk - Funky](../src/transcriptions/Funky.pdf)  
[Monk - Gonhe To Sune](../src/transcriptions/Funky.pdf)  -->
