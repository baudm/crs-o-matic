(function(b){b.fn.paginate=function(a){var e=b.extend({},b.fn.paginate.defaults,a);return this.each(function(){$this=b(this);var g=b.meta?b.extend({},e,$this.data()):e;b.fn.draw(g,$this,g.start)})};var o=0,p=0;if(navigator.appVersion.indexOf("MSIE 7.0")>0)var s="ie7";b.fn.paginate.defaults={count:5,start:12,display:5,border:true,border_color:"#fff",text_color:"#8cc59d",background_color:"black",border_hover_color:"#fff",text_hover_color:"#fff",background_hover_color:"#fff",rotate:true,images:true,
mouse:"slide",onChange:function(){return false}};b.fn.draw=function(a,e,g){if(a.display>a.count)a.display=a.count;$this.empty();if(a.images){var j="jPag-sprevious-img";e="jPag-previous-img";e="jPag-snext-img";var k="jPag-next-img"}else{j="jPag-sprevious";e="jPag-previous";e="jPag-snext";k="jPag-next"}var f=b(document.createElement("a")).addClass("jPag-first").html("First");if(a.rotate)var h=a.images?b(document.createElement("span")).addClass(j):b(document.createElement("span")).addClass(j).html("&laquo;");
j=b(document.createElement("div")).addClass("jPag-control-back");j.append(f).append(h);var c=b(document.createElement("div")).css("overflow","hidden"),q=b(document.createElement("ul")).addClass("jPag-pages"),r;for(k=0;k<a.count;k++){var l=k+1;if(l==g)r=l=b(document.createElement("li")).html('<span class="jPag-current">'+l+"</span>");else l=b(document.createElement("li")).html("<a>"+l+"</a>");q.append(l)}c.append(q);if(a.rotate)var i=a.images?b(document.createElement("span")).addClass(e):b(document.createElement("span")).addClass(e).html("&raquo;");
g=b(document.createElement("a")).addClass("jPag-last").html("Last");var m=b(document.createElement("div")).addClass("jPag-control-front");m.append(i).append(g);$this.addClass("jPaginate").append(j).append(c).append(m);if(a.border){t=a.background_color=="none"?{color:a.text_color,border:"1px solid "+a.border_color}:{color:a.text_color,"background-color":a.background_color,border:"1px solid "+a.border_color};u=a.background_hover_color=="none"?{color:a.text_hover_color,border:"1px solid "+a.border_hover_color}:
{color:a.text_hover_color,"background-color":a.background_hover_color,border:"1px solid "+a.border_hover_color}}else var t=a.background_color=="none"?{color:a.text_color}:{color:a.text_color,"background-color":a.background_color},u=a.background_hover_color=="none"?{color:a.text_hover_color}:{color:a.text_hover_color,"background-color":a.background_hover_color};b.fn.applystyle(a,$this,t,u,f,q,c,m);var n=o-f.parent().width()-3;if(s=="ie7"){c.css("width",n+72+"px");m.css("left",o+6+72+"px")}else{c.css("width",
n+"px");m.css("left",o+6+"px")}if(a.rotate){i.hover(function(){thumbs_scroll_interval=setInterval(function(){var d=c.scrollLeft()+1;c.scrollLeft(d)},20)},function(){clearInterval(thumbs_scroll_interval)});h.hover(function(){thumbs_scroll_interval=setInterval(function(){var d=c.scrollLeft()-1;c.scrollLeft(d)},20)},function(){clearInterval(thumbs_scroll_interval)});if(a.mouse=="press"){i.mousedown(function(){thumbs_mouse_interval=setInterval(function(){var d=c.scrollLeft()+5;c.scrollLeft(d)},20)}).mouseup(function(){clearInterval(thumbs_mouse_interval)});
h.mousedown(function(){thumbs_mouse_interval=setInterval(function(){var d=c.scrollLeft()-5;c.scrollLeft(d)},20)}).mouseup(function(){clearInterval(thumbs_mouse_interval)})}else{h.click(function(){var d=n-10;d=c.scrollLeft()-d;c.animate({scrollLeft:d+"px"})});i.click(function(){var d=n-10;d=c.scrollLeft()+d;c.animate({scrollLeft:d+"px"})})}}f.click(function(){c.animate({scrollLeft:"0px"});c.find("li").eq(0).click()});g.click(function(){c.animate({scrollLeft:p+"px"});c.find("li").eq(a.count-1).click()});
c.find("li").click(function(){r.html("<a>"+r.find(".jPag-current").html()+"</a>");var d=b(this).find("a").html();b(this).html('<span class="jPag-current">'+d+"</span>");r=b(this);b.fn.applystyle(a,b(this).parent().parent().parent(),t,u,f,q,c,m);var v=this.offsetLeft/2;c.scrollLeft();var w=v-n/2;s=="ie7"?c.animate({scrollLeft:v+w-f.parent().width()+52+"px"}):c.animate({scrollLeft:v+w-f.parent().width()+"px"});a.onChange(d)});i=c.find("li").eq(a.start-1);i.attr("id","tmp");h=document.getElementById("tmp").offsetLeft/
2;i.removeAttr("id");i=h-n/2;s=="ie7"?c.animate({scrollLeft:h+i-f.parent().width()+52+"px"}):c.animate({scrollLeft:h+i-f.parent().width()+"px"})};b.fn.applystyle=function(a,e,g,j,k,f){e.find("a").css(g);e.find("span.jPag-current").css(j);e.find("a").hover(function(){b(this).css(j)},function(){b(this).css(g)});e.css("padding-left",k.parent().width()+5+"px");p=0;e.find("li").each(function(h){if(h==a.display-1)o=this.offsetLeft+this.offsetWidth;p+=this.offsetWidth});f.css("width",p+"px")}})(jQuery);
