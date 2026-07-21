import{b as g}from"./index-CqGzBhjA.js";/**
 * @license lucide-vue-next v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const d=g("CameraIcon",[["path",{d:"M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z",key:"1tc9qg"}],["circle",{cx:"12",cy:"13",r:"3",key:"1vg3eu"}]]);function u(s,a=512,f=.82){return new Promise((h,l)=>{const n=URL.createObjectURL(s),c=new Image;c.onload=()=>{URL.revokeObjectURL(n);let{width:e,height:t}=c;e>=t&&e>a?(t=Math.round(t*a/e),e=a):t>a&&(e=Math.round(e*a/t),t=a);const r=document.createElement("canvas");r.width=e,r.height=t;const o=r.getContext("2d");o.fillStyle="#ffffff",o.fillRect(0,0,e,t),o.drawImage(c,0,0,e,t),h(r.toDataURL("image/jpeg",f))},c.onerror=l,c.src=n})}export{d as C,u as r};
