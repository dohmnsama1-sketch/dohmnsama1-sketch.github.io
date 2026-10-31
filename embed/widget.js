/* Meezan calculator embed loader: no cookies, no tracking. Usage:
<div class="meezan-calc" data-calc="roas|markup|profit" data-lang="ar|en"><a href="https://dohmnsama1-sketch.github.io/">Meezan</a></div>
<script src="https://dohmnsama1-sketch.github.io/embed/widget.js" async></script> */
(function(){var B='https://dohmnsama1-sketch.github.io',H={roas:520,markup:460,profit:600,all:680},n=0;
function go(){[].forEach.call(document.querySelectorAll('.meezan-calc:not([data-mz])'),function(d){
var c=d.getAttribute('data-calc')||'',l=d.getAttribute('data-lang')==='en'?'en':'ar',id='mz'+(++n),f=document.createElement('iframe');
if(!H[c])c='';d.setAttribute('data-mz',id);
f.src=B+'/embed/?'+(c?'calc='+c+'&':'')+'lang='+l+'&id='+id;f.title=l==='ar'?'حاسبة ميزان':'Meezan calculator';f.loading='lazy';
f.setAttribute('referrerpolicy','no-referrer');f.style.cssText='width:100%;max-width:560px;height:'+H[c||'all']+'px;border:0;display:block;margin:0 auto';
d.insertBefore(f,d.firstChild)})}
addEventListener('message',function(e){var m=e.data;if(e.origin!==B||!m||!m.mz)return;
var d=document.querySelector('.meezan-calc[data-mz="'+m.id+'"] iframe');if(d&&m.h>100&&m.h<3000)d.style.height=m.h+'px'});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',go);else go()})();
