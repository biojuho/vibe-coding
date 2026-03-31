const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const FEED_STANDARDS = [
  { status: "송아지", roughage: "건초", roughageKg: 1.5, concentrate: "송아지 전용", concentrateKg: 2.0, note: "이유 전: 대용유 급여" },
  { status: "육성우", roughage: "건초+볏짚", roughageKg: 4.0, concentrate: "육성우용", concentrateKg: 3.0, note: "조단백 15% 이상" },
  { status: "번식우", roughage: "볏짚+건초", roughageKg: 5.0, concentrate: "번식우용", concentrateKg: 2.5, note: "체형 유지, 과비 주의" },
  { status: "임신우", roughage: "양질건초", roughageKg: 5.5, concentrate: "번식우용", concentrateKg: 3.0, note: "분만 2개월 전 증량" },
  { status: "비육우", roughage: "볏짚", roughageKg: 1.5, concentrate: "비육전기/후기", concentrateKg: 8.0, note: "마블링 위해 농후사료 비율↑" },
  { status: "씨수소", roughage: "건초+볏짚", roughageKg: 5.0, concentrate: "번식우용", concentrateKg: 3.5, note: "과비 방지, 운동 필수" },
];

async function main() {
  console.log(`Start seeding FeedStandards...`);
  for (const std of FEED_STANDARDS) {
    const feed = await prisma.feedStandard.upsert({
      where: { status: std.status },
      update: std,
      create: std,
    });
    console.log(`Upserted feed standard for ${feed.status}`);
  }
  console.log(`Seeding finished.`);
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error(e);
    await prisma.$disconnect();
    process.exit(1);
  });
