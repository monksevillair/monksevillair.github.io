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

# HTML
<!-- spinning bullshit -->
<img src="./src/templates/images/dozehilz.png" class="rotate" width="400">

