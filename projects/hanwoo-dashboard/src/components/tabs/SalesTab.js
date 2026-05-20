'use client';

import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ReceiptText } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

import MarketPriceWidget from '@/components/widgets/MarketPriceWidget';
import { formatMoney } from '@/lib/utils';
import { createSalesFormValues, salesFormSchema } from '@/lib/formSchemas';
import { PremiumButton } from '@/components/ui/premium-button';
import { PremiumInput, PremiumSelect, PremiumLabel } from '@/components/ui/premium-input';
import { PremiumCard, PremiumCardContent } from '@/components/ui/premium-card';
import EmptyState from '@/components/ui/empty-state';

const errorTextStyle = {
  fontSize: '12px',
  marginTop: '6px',
  color: 'var(--color-danger)',
  fontWeight: 600,
};

export default function SalesTab({
  saleRecords,
  cattleList,
  onCreateSale,
  expenseRecords = [],
  initialMarketPrice = null,
  salesPagination = null,
  quickActionIntent = null,
}) {
  const [isAdding, setIsAdding] = useState(() => quickActionIntent?.actionId === 'record-sale');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(salesFormSchema),
    defaultValues: createSalesFormValues(),
  });

  const processedRecords = useMemo(() => {
    if (!saleRecords) {
      return [];
    }

    return [...saleRecords]
      .map((record) => {
        const cow = cattleList?.find((item) => item.id === record.cattleId) || {};
        const cattleExpenses = expenseRecords.filter((expense) => expense.cattleId === record.cattleId);
        const purchaseCost = cow.purchasePrice || 0;
        const feedCost = cattleExpenses
          .filter((expense) => expense.category === 'feed')
          .reduce((sum, expense) => sum + expense.amount, 0);
        const medicalCost = cattleExpenses
          .filter((expense) => expense.category === 'medicine')
          .reduce((sum, expense) => sum + expense.amount, 0);
        const otherCost = cattleExpenses
          .filter((expense) => expense.category !== 'feed' && expense.category !== 'medicine')
          .reduce((sum, expense) => sum + expense.amount, 0);
        const totalCost = purchaseCost + feedCost + medicalCost + otherCost;
        const hasExpenseData = cattleExpenses.length > 0 || purchaseCost > 0;

        return {
          ...record,
          name: cow.name || '개체명 미등록',
          tagNumber: cow.tagNumber || '이력번호 미등록',
          costs: {
            purchase: purchaseCost,
            feed: feedCost,
            medical: medicalCost,
            other: otherCost,
            total: totalCost,
          },
          profit: hasExpenseData ? record.price - totalCost : null,
          hasExpenseData,
        };
      })
      .sort((first, second) => new Date(second.saleDate) - new Date(first.saleDate));
  }, [saleRecords, cattleList, expenseRecords]);

  const safeTotalSales = useMemo(
    () => processedRecords.reduce((sum, record) => sum + record.price, 0),
    [processedRecords],
  );

  const safeTotalProfit = useMemo(() => {
    const recordsWithProfit = processedRecords.filter((record) => record.profit !== null);
    return recordsWithProfit.reduce((sum, record) => sum + record.profit, 0);
  }, [processedRecords]);

  const safeChartData = useMemo(
    () =>
      processedRecords
        .slice(0, 5)
        .reverse()
        .map((record) => ({
          name: record.name,
          saleAmount: record.price,
          profit: record.profit ?? 0,
        })),
    [processedRecords],
  );

  const toggleAddForm = () => {
    const next = !isAdding;
    setIsAdding(next);

    if (!next) {
      reset(createSalesFormValues());
    }
  };

  const submitSale = async (values) => {
    const saved = await onCreateSale(values);
    if (!saved) {
      return;
    }

    setIsAdding(false);
    reset(createSalesFormValues());
  };

  return (
    <div>
      <MarketPriceWidget initialData={initialMarketPrice} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span aria-hidden="true" style={{ fontSize: '20px', lineHeight: 1 }}>💰</span>
          <span style={{ fontSize: '17px', fontWeight: 800, color: 'var(--color-text)', letterSpacing: '-0.01em' }}>출하 및 매출 분석</span>
        </div>
        <PremiumButton
          variant="outline"
          size="sm"
          onClick={toggleAddForm}
          className="text-[13px] text-green-400 border-green-500/50 hover:bg-green-500/10 px-3 py-1.5 rounded-lg font-bold"
        >
          {isAdding ? '취소' : '+매출 등록'}
        </PremiumButton>
      </div>

      {isAdding ? (
        <form onSubmit={handleSubmit(submitSale)} className="mb-4">
          <PremiumCard className="bg-slate-800/60 w-full mb-4">
            <PremiumCardContent className="p-4">
              <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>새 매출 기록 등록</div>
              <div style={{ display: 'grid', gap: '10px' }}>
                <div>
                  <PremiumLabel htmlFor="sale-date">출하일자</PremiumLabel>
                  <PremiumInput
                    id="sale-date"
                    type="date"
                    {...register('saleDate')}
                    aria-invalid={Boolean(errors.saleDate)}
                    aria-describedby={errors.saleDate ? "sale-date-error" : undefined}
                    hasError={!!errors.saleDate}
                  />
                  {errors.saleDate ? <div id="sale-date-error" role="alert" style={errorTextStyle}>{errors.saleDate.message}</div> : null}
                </div>

                <div>
                  <PremiumLabel htmlFor="sale-price">판매 가격 (원)</PremiumLabel>
                  <PremiumInput
                    id="sale-price"
                    type="number"
                    {...register('price')}
                    placeholder="예: 8500000"
                    aria-invalid={Boolean(errors.price)}
                    aria-describedby={errors.price ? "sale-price-error" : undefined}
                    hasError={!!errors.price}
                  />
                  {errors.price ? <div id="sale-price-error" role="alert" style={errorTextStyle}>{errors.price.message}</div> : null}
                </div>

                <div>
                  <PremiumLabel htmlFor="sale-cattle">출하 개체</PremiumLabel>
                  <PremiumSelect
                    id="sale-cattle"
                    {...register('cattleId')}
                    aria-invalid={Boolean(errors.cattleId)}
                    aria-describedby={errors.cattleId ? "sale-cattle-error" : undefined}
                    hasError={!!errors.cattleId}
                  >
                    <option value="" className="bg-slate-900">선택해 주세요</option>
                    {cattleList?.map((cow) => (
                      <option key={cow.id} value={cow.id} className="bg-slate-900">
                        {cow.name} ({cow.tagNumber})
                      </option>
                    ))}
                  </PremiumSelect>
                  {errors.cattleId ? <div id="sale-cattle-error" role="alert" style={errorTextStyle}>{errors.cattleId.message}</div> : null}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <PremiumLabel htmlFor="sale-grade">등급</PremiumLabel>
                    <PremiumSelect
                      id="sale-grade"
                      {...register('grade')}
                      aria-invalid={Boolean(errors.grade)}
                      aria-describedby={errors.grade ? "sale-grade-error" : undefined}
                      hasError={!!errors.grade}
                    >
                      <option value="1++" className="bg-slate-900">1++</option>
                      <option value="1+" className="bg-slate-900">1+</option>
                      <option value="1" className="bg-slate-900">1</option>
                      <option value="2" className="bg-slate-900">2</option>
                      <option value="3" className="bg-slate-900">3</option>
                    </PremiumSelect>
                    {errors.grade ? <div id="sale-grade-error" role="alert" style={errorTextStyle}>{errors.grade.message}</div> : null}
                  </div>

                  <div>
                    <PremiumLabel htmlFor="sale-purchaser">구매처</PremiumLabel>
                    <PremiumInput
                      id="sale-purchaser"
                      {...register('purchaser')}
                      placeholder="예: 남원축협"
                      aria-invalid={Boolean(errors.purchaser)}
                      aria-describedby={errors.purchaser ? "sale-purchaser-error" : undefined}
                      hasError={!!errors.purchaser}
                    />
                    {errors.purchaser ? <div id="sale-purchaser-error" role="alert" style={errorTextStyle}>{errors.purchaser.message}</div> : null}
                  </div>
                </div>

                <PremiumButton
                  type="submit"
                  disabled={!cattleList?.length}
                  className="w-full py-3 mt-2 rounded-lg"
                  variant="primary"
                  glow
                >
                  등록하기
                </PremiumButton>

                {!cattleList?.length ? (
                  <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                    먼저 개체를 등록해야 판매 기록을 추가할 수 있습니다.
                  </div>
                ) : null}
              </div>
            </PremiumCardContent>
          </PremiumCard>
        </form>
      ) : null}

      <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '10px', marginBottom: '10px' }}>
        <PremiumCard className="bg-linear-to-br border-primary/20 flex-1 min-w-[140px] from-orange-400 to-orange-600">
          <PremiumCardContent className="p-4 text-white">
            <div style={{ fontSize: '11px', opacity: 0.7 }}>총 누적 매출</div>
            <div style={{ fontSize: '20px', fontWeight: 800, fontFamily: "'Outfit',sans-serif" }}>
              {formatMoney(safeTotalSales / 10000)}만
            </div>
          </PremiumCardContent>
        </PremiumCard>
        <PremiumCard className="flex-1 min-w-[140px]">
          <PremiumCardContent className="p-4">
            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>평균 수익률</div>
            <div
              style={{
                fontSize: '20px',
                fontWeight: 800,
                color: safeTotalProfit >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                fontFamily: "'Outfit',sans-serif",
              }}
            >
              {safeTotalSales > 0 ? ((safeTotalProfit / safeTotalSales) * 100).toFixed(1) : 0}%
            </div>
          </PremiumCardContent>
        </PremiumCard>
      </div>

      <PremiumCard className="mb-4">
        <PremiumCardContent className="p-5">
          <div style={{ fontSize: '13px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text)' }}>최근 5건 수익 분석</div>
          <div style={{ height: '200px', fontSize: '10px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={safeChartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} tickFormatter={(value) => `${value / 10000}`} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  formatter={(value) => `${formatMoney(value)}원`}
                />
                <Legend />
                <Bar dataKey="saleAmount" name="판매금액" fill="#BCAAA4" radius={[4, 4, 0, 0]} barSize={20} />
                <Bar dataKey="profit" name="수익" fill="var(--color-primary-light)" radius={[4, 4, 0, 0]} barSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </PremiumCardContent>
      </PremiumCard>

      <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '10px', color: 'var(--color-text)' }}>출하 이력</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {processedRecords.length === 0 ? (
          <EmptyState
            icon={ReceiptText}
            title="출하 내역이 없습니다"
            description={
              cattleList?.length
                ? '첫 출하 기록을 남기면 매출, 등급, 수익 분석 차트가 바로 채워집니다.'
                : '개체를 먼저 등록하면 출하 기록과 수익 분석을 연결할 수 있습니다.'
            }
            actionLabel={cattleList?.length ? '매출 기록' : '개체 등록 필요'}
            onAction={() => setIsAdding(true)}
            disabled={!cattleList?.length}
          />
        ) : (
          processedRecords.map((record, index) => (
            <PremiumCard key={record.id || index} className="p-0">
              <PremiumCardContent className="p-3.5">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '14px' }}>
                      {record.name} ({record.grade})
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>{record.tagNumber}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 800, fontSize: '15px', color: 'var(--color-primary-light)' }}>
                      {formatMoney(record.price)}원
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>{record.auctionLocation || record.purchaser}</div>
                  </div>
                </div>

                <div
                  className="bg-slate-900/30 rounded-lg p-2 flex justify-between text-xs"
                >
                  {record.hasExpenseData ? (
                    <>
                      <span className="text-slate-400">총 비용: {formatMoney(record.costs.total)}원</span>
                      <span
                        className={record.profit >= 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}
                      >
                        순수익: {record.profit >= 0 ? '+' : ''}
                        {formatMoney(record.profit)}원
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="text-slate-500 italic">비용 미등록</span>
                      <span className="text-slate-500">수익 추정 불가</span>
                    </>
                  )}
                </div>
              </PremiumCardContent>
            </PremiumCard>
          ))
        )}
      </div>

      {salesPagination?.hasMore && (
        <>
          <PremiumButton
            variant="secondary"
            onClick={() => salesPagination.loadMore()}
            disabled={salesPagination.isLoading}
            aria-busy={salesPagination.isLoading}
            className="w-full mt-3 py-3"
          >
            {salesPagination.isLoading ? '불러오는 중...' : '이전 기록 더 보기'}
          </PremiumButton>
          {salesPagination.loadError ? (
            <p
              role="status"
              aria-live="polite"
              className="mt-2 text-center text-xs font-semibold text-red-300"
            >
              {salesPagination.loadError}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}
