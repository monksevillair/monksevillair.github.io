# Title
Monk's Evil Lair

# Style
.rotate {
transform-origin: 52% 52%;
animation: rotation 8s infinite linear;
}

.shrink {
animation: shrinking 5s infinite linear alternate;
animation-timing-function: ease-in-out;
}

@keyframes rotation {
from {
transform: rotate(0deg);
}
to {
transform: rotate(-359deg);
}
}

@keyframes shrinking {
from {
transform:scale(1);
}
to {
transform:scale(1.2);
}
}

.scroll {
  overflow: hidden; /* Hide scrollbars */
  background-color: transparent;
}

.scroll a:hover {
  background-color: transparent;

}

.scroll a:link {
	  color: {color_link};
	  text-decoration: underline;
	  /*background-color: {color_accent_light};*/

	  /*font-weight: bolder;*/
	  border-bottom:0px solid;
}

.quote {
	  font-weight: bold;
	  font-style: italic;
	  text-align: right;
}

# HTML
<!-- spinninsdg bullshit -->
<center>
<a href="./music/music.html">
<img src="./src/templates/images/dozehilz.png" class="rotate" width="400">
</a>
</center>

{gen_quote}



