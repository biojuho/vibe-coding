const { PrismaClient } = require('@prisma/client');
require('dotenv').config();
const prisma = new PrismaClient();

const bcrypt = require('bcrypt');

// building_1, building_2, building_3 — seed-buildings.js 와 동일
const BUILDINGS = [
  { id: "building_1", name: "1동 (번식우)" },
  { id: "building_2", name: "2동 (비육우)" },
  { id: "building_3", name: "3동 (송아지/격리)" }
];

function getMonthAge(birthDate) {
  const today = new Date();
  const birth = new Date(birthDate);
  return (today.getFullYear() - birth.getFullYear()) * 12 + (today.getMonth() - birth.getMonth());
}

async function main() {
  console.log('Start seeding ...');

  // 의존성 순서대로 삭제 (FK 위반 방지)
  await prisma.cattleHistory.deleteMany({});
  await prisma.expenseRecord.deleteMany({});
  await prisma.scheduleEvent.deleteMany({});
  await prisma.salesRecord.deleteMany({});
  await prisma.feedRecord.deleteMany({});
  await prisma.cattle.deleteMany({});
  await prisma.user.deleteMany({});

  // 1. Admin User
  const hashedPassword = await bcrypt.hash("admin123", 10);
  await prisma.user.create({
    data: { username: "admin", password: hashedPassword }
  });
  console.log('Admin user created (admin / admin123)');

  // 2. 이름 풀
  const names = ["금이","은이","별이","달이","꽃이","봄이","가을이","겨울이","하늘이","구름이","바람이","해님이","산이","강이","들이","숲이","미르","다솜","한별","아라","이슬","나래","보람","소망","진이","석이","돌이","복이","순이","영이","철이","만이","초롱이","단비","새별","가온","다온","한솔","늘봄","예솔"];
  const today = new Date();
  let idx = 0;
  const createdCattle = [];

  // 3. Cattle 시드
  for (let bi = 0; bi < BUILDINGS.length; bi++) {
    const building = BUILDINGS[bi];
    for (let pen = 1; pen <= 12; pen++) {
      const cnt = Math.floor(Math.random() * 4) + 1;
      for (let c = 0; c < cnt; c++) {
        const isFemale = Math.random() > 0.2;
        const by = 2020 + Math.floor(Math.random() * 5);
        const bm = Math.floor(Math.random() * 12);
        const bd = new Date(by, bm, Math.floor(Math.random() * 28) + 1);
        const ma = getMonthAge(bd);

        let st = ma <= 6 ? "송아지" : ma <= 14 ? "육성우" : isFemale ? (Math.random() > 0.5 ? "번식우" : "임신우") : (bi === 1 ? "비육우" : "씨수소");

        let lastEstrus = null;
        if (st === "번식우" && isFemale) {
          lastEstrus = new Date(today);
          lastEstrus.setDate(lastEstrus.getDate() - Math.floor(Math.random() * 21));
        }

        let pregnancyDate = null;
        if (st === "임신우") {
          pregnancyDate = new Date(today);
          pregnancyDate.setMonth(pregnancyDate.getMonth() - Math.floor(Math.random() * 8) - 1);
        }

        const tagNumber = `KR${bi + 1}${String(pen).padStart(2, "0")}-${String(idx + 1).padStart(4, "0")}`;
        const weight = ma <= 6 ? 80 + ma * 20 : 350 + ma * 10;

        // 구매가격: 송아지 200~400만, 성우 300~600만
        const purchasePrice = ma <= 6
          ? 2000000 + Math.floor(Math.random() * 2000000)
          : 3000000 + Math.floor(Math.random() * 3000000);
        // 구매일: 생후 1~3개월 사이
        const purchaseDate = new Date(bd);
        purchaseDate.setMonth(purchaseDate.getMonth() + 1 + Math.floor(Math.random() * 2));

        const created = await prisma.cattle.create({
          data: {
            tagNumber,
            name: names[idx % names.length],
            birthDate: bd,
            gender: isFemale ? "암" : "수",
            status: st,
            weight,
            buildingId: building.id,
            penNumber: pen,
            geneticFather: `KPN-${1000 + Math.floor(Math.random() * 9000)}`,
            geneticMother: `KPN-${1000 + Math.floor(Math.random() * 9000)}`,
            geneticGrade: ["1++", "1+", "1", "2"][Math.floor(Math.random() * 4)],
            lastEstrus,
            pregnancyDate,
            purchasePrice,
            purchaseDate,
            memo: "",
          }
        });

        // 이력 기록: 등록
        await prisma.cattleHistory.create({
          data: {
            cattleId: created.id,
            eventType: "purchase",
            eventDate: purchaseDate,
            description: `신규 등록: ${names[idx % names.length]} (${tagNumber})`,
            metadata: JSON.stringify({ purchasePrice }),
          }
        });

        createdCattle.push(created);
        idx++;
      }
    }
  }

  console.log(`Created ${createdCattle.length} cattle with histories`);

  // 4. Sales Records — 실제 비육우/성우 ID 참조
  const sellableCattle = createdCattle.filter(c => c.status === "비육우" || c.status === "씨수소");
  const grades = ["1++", "1+", "1", "2", "3"];
  const saleCount = Math.min(15, sellableCattle.length);

  for (let i = 0; i < saleCount; i++) {
    const cow = sellableCattle[i];
    const saleDate = new Date(2024, Math.floor(Math.random() * 12), Math.floor(Math.random() * 28) + 1);
    const grade = grades[Math.floor(Math.random() * 5)];
    const basePrice = grade === "1++" ? 28000 : grade === "1+" ? 24000 : grade === "1" ? 20000 : grade === "2" ? 16000 : 12000;
    const saleWeight = 650 + Math.floor(Math.random() * 150);
    const salePrice = Math.floor(basePrice * saleWeight / 1000 * (0.9 + Math.random() * 0.2));

    await prisma.salesRecord.create({
      data: {
        saleDate,
        price: salePrice * 10000,
        purchaser: ["남원", "장수", "익산"][Math.floor(Math.random() * 3)] + " 축산물공판장",
        grade,
        cattleId: cow.id,
      }
    });

    // 출하 이력
    await prisma.cattleHistory.create({
      data: {
        cattleId: cow.id,
        eventType: "sale",
        eventDate: saleDate,
        description: `출하: ${(salePrice * 10000).toLocaleString()}원 (등급: ${grade})`,
        metadata: JSON.stringify({ price: salePrice * 10000, grade }),
      }
    });
  }

  console.log(`Created ${saleCount} sales records`);

  // 5. 샘플 ExpenseRecord (최근 6개월간 비용 데이터)
  const categories = ["feed", "medicine", "labor", "other"];
  const categoryAmounts = {
    feed: { min: 500000, max: 2000000 },
    medicine: { min: 50000, max: 300000 },
    labor: { min: 200000, max: 500000 },
    other: { min: 30000, max: 150000 },
  };
  const categoryDescs = {
    feed: ["배합사료 구입", "볏짚 구입", "건초 구입", "대용유 구입"],
    medicine: ["구충제 투약", "백신 접종", "수의사 진료", "소독약품"],
    labor: ["임시 인건비", "축사 청소 용역", "사료 운반 인력"],
    other: ["축사 보수", "전기료", "수도료", "기타 소모품"],
  };

  let expenseCount = 0;
  for (let monthOffset = 0; monthOffset < 6; monthOffset++) {
    const expMonth = new Date(today.getFullYear(), today.getMonth() - monthOffset, 1);

    for (const cat of categories) {
      // 사료는 월 2~3건, 나머지는 0~1건
      const count = cat === "feed" ? 2 + Math.floor(Math.random() * 2) : Math.floor(Math.random() * 2);
      for (let i = 0; i < count; i++) {
        const range = categoryAmounts[cat];
        const amount = range.min + Math.floor(Math.random() * (range.max - range.min));
        const descs = categoryDescs[cat];
        const day = 1 + Math.floor(Math.random() * 27);
        const expDate = new Date(expMonth.getFullYear(), expMonth.getMonth(), day);

        // 사료비는 축사에 연결, 약품비는 개체에 연결
        let cattleId = null;
        let buildingId = null;
        if (cat === "feed") {
          buildingId = BUILDINGS[Math.floor(Math.random() * BUILDINGS.length)].id;
        } else if (cat === "medicine" && createdCattle.length > 0) {
          cattleId = createdCattle[Math.floor(Math.random() * createdCattle.length)].id;
        }

        await prisma.expenseRecord.create({
          data: {
            date: expDate,
            cattleId,
            buildingId,
            category: cat,
            amount,
            description: descs[Math.floor(Math.random() * descs.length)],
          }
        });
        expenseCount++;
      }
    }
  }

  console.log(`Created ${expenseCount} expense records`);
  console.log('Seeding finished.');
}

main()
  .then(async () => { await prisma.$disconnect(); })
  .catch(async (e) => { console.error(e); await prisma.$disconnect(); process.exit(1); });
