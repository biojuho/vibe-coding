'use client';

import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

import MarketPriceWidget from '@/components/widgets/MarketPriceWidget';
import { formatMoney } from '@/lib/utils';
import { createSalesFormValues, salesFormSchema } from '@/lib/formSchemas';

const errorTextStyle = {
  fontSize: '12px',
  marginTop: '6px',
  color: 'var(--color-danger)',
  fontWeight: 600,
};

export default function SalesTab({ saleRecords, cattleList, onCreateSale, expenseRecords = [], initialMarketPrice = null, salesPagination = null }) {
  const [isAdding, setIsAdding] = useState(false);

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
          name: cow.name || 'Unknown',
          tagNumber: cow.tagNumber || '000-0000-0000',
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

  const submitSale = (values) => {
    onCreateSale(values);
    setIsAdding(false);
    reset(createSalesFormValues());
  };

  return (
    <div>
      <MarketPriceWidget initialData={initialMarketPrice} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--color-text)' }}>출하 및 매출 분석</div>
        <button
          type="button"
          onClick={toggleAddForm}
          style={{
            fontSize: '13px',
            fontWeight: 700,
            color: 'var(--color-success)',
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-success)',
            borderRadius: '8px',
            padding: '6px 12px',
            cursor: 'pointer',
          }}
        >
          {isAdding ? '취소' : '+매출 등록'}
        </button>
      </div>

      {isAdding ? (
        <form
          onSubmit={handleSubmit(submitSale)}
          style={{
            background: 'var(--color-bg)',
            borderRadius: '14px',
            padding: '16px',
            marginBottom: '16px',
            border: '1px solid var(--color-border)',
          }}
        >
          <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>새 매출 기록 등록</div>
          <div style={{ display: 'grid', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>출하일자</label>
              <input
                type="date"
                {...register('saleDate')}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--color-border)' }}
              />
              {errors.saleDate ? <div style={errorTextStyle}>{errors.saleDate.message}</div> : null}
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>판매 가격 (원)</label>
              <input
                type="number"
                {...register('price')}
                placeholder="예: 8500000"
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--color-border)' }}
              />
              {errors.price ? <div style={errorTextStyle}>{errors.price.message}</div> : null}
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>출하 개체</label>
              <select
                {...register('cattleId')}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--color-border)' }}
              >
                <option value="">선택해 주세요</option>
                {cattleList?.map((cow) => (
                  <option key={cow.id} value={cow.id}>
                    {cow.name} ({cow.tagNumber})
                  </option>
                ))}
              </select>
              {errors.cattleId ? <div style={errorTextStyle}>{errors.cattleId.message}</div> : null}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>등급</label>
                <select
                  {...register('grade')}
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--color-border)' }}
                >
                  <option value="1++">1++</option>
                  <option value="1+">1+</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                </select>
                {errors.grade ? <div style={errorTextStyle}>{errors.grade.message}</div> : null}
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>구매처</label>
                <input
                  {...register('purchaser')}
                  placeholder="예: 남원축협"
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--color-border)' }}
                />
                {errors.purchaser ? <div style={errorTextStyle}>{errors.purchaser.message}</div> : null}
              </div>
            </div>

            <button
              type="submit"
              disabled={!cattleList?.length}
              style={{
                width: '100%',
                padding: '12px',
                background: 'var(--color-success)',
                color: 'white',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 700,
                marginTop: '8px',
                cursor: cattleList?.length ? 'pointer' : 'not-allowed',
                opacity: cattleList?.length ? 1 : 0.6,
              }}
            >
              등록하기
            </button>

            {!cattleList?.length ? (
              <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                먼저 개체를 등록해야 판매 기록을 추가할 수 있습니다.
              </div>
            ) : null}
          </div>
        </form>
      ) : null}

      <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '10px', marginBottom: '10px' }}>
        <div
          style={{
            background: 'linear-gradient(135deg, var(--color-primary), var(--color-primary-dark))',
            borderRadius: '14px',
            padding: '16px',
            flex: '1 0 140px',
            color: 'white',
          }}
        >
          <div style={{ fontSize: '11px', opacity: 0.7 }}>총 누적 매출</div>
          <div style={{ fontSize: '20px', fontWeight: 800, fontFamily: "'Outfit',sans-serif" }}>
            {formatMoney(safeTotalSales / 10000)}만
          </div>
        </div>
        <div
          style={{
            background: 'var(--color-bg-card)',
            borderRadius: '14px',
            padding: '16px',
            flex: '1 0 140px',
            border: '1px solid var(--color-border)',
          }}
        >
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
        </div>
      </div>

      <div
        style={{
          background: 'var(--color-bg-card)',
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '16px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
        }}
      >
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
      </div>

      <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '10px', color: 'var(--color-text)' }}>출하 이력</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {processedRecords.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-muted)' }}>출하 내역이 없습니다.</div>
        ) : (
          processedRecords.map((record, index) => (
            <div
              key={record.id || index}
              style={{
                background: 'var(--color-bg-card)',
                borderRadius: '14px',
                padding: '14px',
                border: '1px solid var(--color-border)',
              }}
            >
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
                style={{
                  background: 'var(--color-bg)',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '12px',
                }}
              >
                {record.hasExpenseData ? (
                  <>
                    <span style={{ color: 'var(--color-text-secondary)' }}>총 비용: {formatMoney(record.costs.total)}원</span>
                    <span
                      style={{
                        fontWeight: 700,
                        color: record.profit >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                      }}
                    >
                      순수익: {record.profit >= 0 ? '+' : ''}
                      {formatMoney(record.profit)}원
                    </span>
                  </>
                ) : (
                  <>
                    <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>비용 미등록</span>
                    <span style={{ color: 'var(--color-text-muted)' }}>수익 추정 불가</span>
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {salesPagination?.hasMore && (
        <button
          type="button"
          onClick={() => salesPagination.loadMore()}
          disabled={salesPagination.isLoading}
          style={{
            width: '100%',
            padding: '12px',
            marginTop: '12px',
            background: 'var(--color-bg-card)',
            color: 'var(--color-text-secondary)',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
            fontWeight: 700,
            fontSize: '13px',
            cursor: salesPagination.isLoading ? 'wait' : 'pointer',
            opacity: salesPagination.isLoading ? 0.6 : 1,
          }}
        >
          {salesPagination.isLoading ? '불러오는 중...' : '이전 기록 더 보기'}
        </button>
      )}
    </div>
  );
}
