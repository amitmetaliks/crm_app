import{e as a,D as u,x as y,o as s,c as i,a as c,F as p,k,h as x,i as b,n as o,m as v,y as _,t as w,u as f,R as g,d as V}from"./index-aupCaLnA.js";/**
 * @license lucide-vue-next v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const M=a("CirclePlusIcon",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["path",{d:"M8 12h8",key:"1wcyev"}],["path",{d:"M12 8v8",key:"napkw2"}]]);/**
 * @license lucide-vue-next v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const C=a("ClipboardListIcon",[["rect",{width:"8",height:"4",x:"8",y:"2",rx:"1",ry:"1",key:"tgr4d6"}],["path",{d:"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2",key:"116196"}],["path",{d:"M12 11h4",key:"1jrz19"}],["path",{d:"M12 16h4",key:"n85exb"}],["path",{d:"M8 11h.01",key:"1dfujw"}],["path",{d:"M8 16h.01",key:"18s6g9"}]]);/**
 * @license lucide-vue-next v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const N=a("HouseIcon",[["path",{d:"M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8",key:"5wwlr5"}],["path",{d:"M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",key:"1d0kgt"}]]);/**
 * @license lucide-vue-next v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const S=a("MenuIcon",[["line",{x1:"4",x2:"20",y1:"12",y2:"12",key:"1e0a9i"}],["line",{x1:"4",x2:"20",y1:"6",y2:"6",key:"1owob3"}],["line",{x1:"4",x2:"20",y1:"18",y2:"18",key:"yk5zj1"}]]);/**
 * @license lucide-vue-next v0.460.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const A=a("StoreIcon",[["path",{d:"m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7",key:"ztvudi"}],["path",{d:"M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8",key:"1b2hhj"}],["path",{d:"M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4",key:"2ebpfo"}],["path",{d:"M2 7h20",key:"1fcdvo"}],["path",{d:"M22 7v3a2 2 0 0 1-2 2a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 16 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 12 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 8 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 4 12a2 2 0 0 1-2-2V7",key:"6c3vgh"}]]),D={class:"fixed inset-x-0 bottom-0 z-40 px-3 pb-2",style:{"padding-bottom":"max(0.5rem, env(safe-area-inset-bottom))"}},I={class:"mx-auto grid max-w-lg grid-cols-5 rounded-[1.4rem] border border-black/5 bg-white/95 px-1 shadow-[0_12px_40px_rgba(23,32,51,0.16)] backdrop-blur-xl dark:border-white/10 dark:bg-navy-800/95"},E={key:0,class:"absolute bottom-1 h-1 w-1 rounded-full bg-saffron"},B={__name:"BottomNav",setup(j){const n=u(),l=[{name:"Dashboard",label:"Home",icon:N},{name:"Visits",label:"Visits",icon:C},{name:"NewVisit",label:"Visit",icon:M},{name:"Customers",label:"Dealers",icon:A},{name:"More",label:"More",icon:S}],d=["Visits","VisitDetail"],h=["Customers","CustomerDetail"];function r(t){return t==="Visits"?d.includes(n.name):t==="Customers"?h.includes(n.name):n.name===t}return(t,z)=>{const m=y("router-link");return s(),i("nav",D,[c("div",I,[(s(),i(p,null,k(l,e=>x(m,{key:e.name,to:{name:e.name},class:o(["relative flex min-h-[4rem] flex-col items-center justify-center gap-1 text-[11px]",[r(e.name)?"aa-nav-active font-semibold":"text-gray-400",e.name==="NewVisit"?"-mt-5":""]])},{default:b(()=>[c("span",{class:o(["flex items-center justify-center",e.name==="NewVisit"?"h-14 w-14 rounded-2xl bg-saffron text-navy-800 shadow-[0_8px_22px_rgba(226,164,59,0.34)]":"h-7 w-10 rounded-xl"])},[(s(),v(_(e.icon),{class:o(e.name==="NewVisit"?"h-7 w-7":"h-5 w-5"),"stroke-width":r(e.name)?2.4:1.8},null,8,["class","stroke-width"]))],2),c("span",{class:o(e.name==="NewVisit"?"font-bold text-navy-700":"")},w(f(g)(e.label)),3),r(e.name)&&e.name!=="NewVisit"?(s(),i("span",E)):V("",!0)]),_:2},1032,["to","class"])),64))])])}}};export{A as S,B as _};
