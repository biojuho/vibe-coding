import { BUILDINGS, TODAY } from './constants';
import { getMonthAge } from './utils';

export function generateSampleData() {
  const names=["금이","은이","별이","달이","꽃이","봄이","가을이","겨울이","하늘이","구름이","바람이","해님이","산이","강이","들이","숲이","미르","다솜","한별","아라","이슬","나래","보람","소망","진이","석이","돌이","복이","순이","영이","철이","만이","초롱이","단비","새별","가온","다온","한솔","늘봄","예솔"];
  const cattle=[];let idx=0;
  BUILDINGS.forEach((b,bi)=>{for(let pen=1;pen<=12;pen++){const cnt=Math.floor(Math.random()*4)+1;for(let c=0;c<cnt;c++){
    const isFemale=Math.random()>0.2;const by=2020+Math.floor(Math.random()*5);const bm=Math.floor(Math.random()*12);
    const bd=new Date(by,bm,Math.floor(Math.random()*28)+1);const ma=getMonthAge(bd);
    let st=ma<=6?"송아지":ma<=14?"육성우":isFemale?(Math.random()>0.5?"번식우":"임신우"):(bi===1?"비육우":"씨수소");
    let le=null;if(st==="번식우"&&isFemale){le=new Date(TODAY);le.setDate(le.getDate()-Math.floor(Math.random()*21));}
    let pd=null;if(st==="임신우"){pd=new Date(TODAY);pd.setMonth(pd.getMonth()-Math.floor(Math.random()*8)-1);}
    // Generate weight history
    const weightHistory = [];
    for(let m=0;m<Math.min(ma,12);m++){
      const date = new Date(TODAY);date.setMonth(date.getMonth()-m);
      const baseWeight = ma<=6?80+(ma-m)*18:350+(ma-m)*12;
      weightHistory.unshift({date:date.toISOString().split('T')[0], weight: Math.max(50, baseWeight + Math.floor(Math.random()*20-10))});
    }
    cattle.push({id:`s_${idx}`,tagNumber:`KR${bi+1}${String(pen).padStart(2,"0")}-${String(idx+1).padStart(4,"0")}`,name:names[idx%names.length],
      buildingId:b.id,penNumber:pen,gender:isFemale?"암":"수",birthDate:bd.toISOString(),weight:ma<=6?80+ma*20:350+ma*10,status:st,
      geneticInfo:{father:`KPN-${1000+Math.floor(Math.random()*9000)}`,mother:`KPN-${1000+Math.floor(Math.random()*9000)}`,grade:["1++","1+","1","2"][Math.floor(Math.random()*4)]},
      lastEstrus:le?.toISOString()||null,pregnancyDate:pd?.toISOString()||null,lastVaccination:new Date(2024,Math.floor(Math.random()*12),Math.floor(Math.random()*28)+1).toISOString(),
      weightHistory, memo:""});
    idx++;}}});
  return cattle;
}

export function generateSaleRecords() {
  const grades = ["1++", "1+", "1", "2", "3"];
  const records = [];
  for (let i = 0; i < 15; i++) {
    const saleDate = new Date(2024, Math.floor(Math.random()*12), Math.floor(Math.random()*28)+1);
    const grade = grades[Math.floor(Math.random()*5)];
    const basePrice = grade==="1++"?28000:grade==="1+"?24000:grade==="1"?20000:grade==="2"?16000:12000;
    const weight = 650 + Math.floor(Math.random()*150);
    const salePrice = Math.floor(basePrice * weight / 1000 * (0.9 + Math.random()*0.2));
    const feedCost = Math.floor(3500000 + Math.random()*1500000);
    const vetCost = Math.floor(200000 + Math.random()*300000);
    const otherCost = Math.floor(100000 + Math.random()*200000);
    records.push({
      id: `sale_${i}`, tagNumber: `KR${Math.floor(Math.random()*3)+1}00-${String(i+100).padStart(4,"0")}`,
      name: ["금이","은이","별이","달이","꽃이","봄이"][Math.floor(Math.random()*6)],
      saleDate: saleDate.toISOString(), monthAge: 28+Math.floor(Math.random()*6),
      weight, grade, salePrice: salePrice * 10000,
      costs: { feed: feedCost, vet: vetCost, other: otherCost, total: feedCost+vetCost+otherCost },
      profit: salePrice * 10000 - (feedCost+vetCost+otherCost),
      auctionLocation: ["남원","장수","익산"][Math.floor(Math.random()*3)] + " 축산물공판장",
    });
  }
  return records.sort((a,b) => new Date(b.saleDate) - new Date(a.saleDate));
}

export function getMarketPrice() {
  return new Promise((resolve) => {
    setTimeout(() => {
      // Base price around 18,000 ~ 20,000 KRW
      const base = 19000;
      const fluctuation = Math.floor(Math.random() * 500 - 250); 
      const currentPrice = base + fluctuation;
      const change = fluctuation; 
      const trend = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
      
      resolve({
        currentPrice,
        change,
        trend,
        timestamp: new Date().toISOString()
      });
    }, 500); // Simulate network delay
  });
}
