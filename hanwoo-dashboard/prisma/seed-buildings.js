const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const DEFAULT_BUILDINGS = [
  { id: "building_1", name: "1동 (번식우)", penCount: 32 },
  { id: "building_2", name: "2동 (비육우)", penCount: 32 },
  { id: "building_3", name: "3동 (육성우)", penCount: 32 }
];

async function main() {
  console.log('Seeding default buildings...');

  for (const b of DEFAULT_BUILDINGS) {
    await prisma.building.upsert({
      where: { id: b.id },
      update: {},
      create: {
        id: b.id,
        name: b.name,
        penCount: b.penCount
      }
    });
  }

  console.log('Default buildings ensured.');
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
