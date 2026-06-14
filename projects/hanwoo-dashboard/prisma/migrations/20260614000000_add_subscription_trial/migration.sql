-- AlterTable: add trialEndDate to Subscription for free trial tracking
ALTER TABLE "Subscription" ADD COLUMN "trialEndDate" TIMESTAMP(3);
