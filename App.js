import React, { useState, useRef } from 'react';
import html2canvas from 'html2canvas';
import JSZip from 'jszip';

function App() {
  const [inputText, setInputText] = useState('');
  const [parsedData, setParsedData] = useState(null);
  const [showExpenseReport, setShowExpenseReport] = useState(false);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const RATE_PER_KM = 15;
  const DAILY_ALLOWANCE = 200;
  const [calculationDate] = useState(new Date().toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }));

  const formatDistance = (distance) => {
    return Number(distance).toFixed(1);
  };

  const calculateTransportationFee = (distance) => {
    return Math.floor(distance * RATE_PER_KM);
  };

  const formatRouteAndDistance = (details) => {
    return details.map(detail => 
      `${detail.route}(${formatDistance(detail.distance)}km)`
    ).join('\n');
  };

  const EntryList = ({ entries, isExpenseReportShown }) => {
    const sortedEntries = entries.sort((a, b) => {
      const getDateValue = (date) => {
        const [month, day] = date.split('/').map(Number);
        return month * 100 + day;
      };

      const dateA = getDateValue(a.date);
      const dateB = getDateValue(b.date);

      if (dateA === dateB) {
        return a.id - b.id;
      }
      return dateB - dateA;
    });

    // 1行あたりの高さを計算（ヘッダー含む）
    const rowHeight = 31; // px
    const headerHeight = 35; // px
    const tableHeight = isExpenseReportShown
      ? headerHeight + (rowHeight * 7)  // 精算書表示時: 7行
      : headerHeight + (rowHeight * 20); // データ解析時: 20行

    return (
      <div style={{ marginBottom: '20px' }}>
        <h2>交通費データ一覧（全{entries.length}件）</h2>
        <div style={{ 
          height: `${tableHeight}px`,
          overflowY: 'auto',
          border: '1px solid #ddd',
          borderRadius: '4px',
          transition: 'height 0.3s ease-in-out'
        }}>
          <table style={{ 
            width: '100%', 
            borderCollapse: 'collapse',
            backgroundColor: '#fff'
          }}>
            <thead style={{ 
              position: 'sticky',
              top: 0,
              backgroundColor: '#f5f5f5',
              zIndex: 1
            }}>
              <tr>
                <th style={{
                  ...tableHeaderStyle,
                  padding: '8px 6px',
                  borderBottom: '2px solid #ddd',
                  fontSize: '0.9em'
                }}>日付</th>
                <th style={{
                  ...tableHeaderStyle,
                  padding: '8px 6px',
                  borderBottom: '2px solid #ddd',
                  fontSize: '0.9em'
                }}>担当者</th>
                <th style={{
                  ...tableHeaderStyle,
                  padding: '8px 6px',
                  borderBottom: '2px solid #ddd',
                  fontSize: '0.9em'
                }}>経路</th>
                <th style={{
                  ...tableHeaderStyle,
                  padding: '8px 6px',
                  borderBottom: '2px solid #ddd',
                  fontSize: '0.9em'
                }}>距離(km)</th>
                <th style={{
                  ...tableHeaderStyle,
                  padding: '8px 6px',
                  borderBottom: '2px solid #ddd',
                  fontSize: '0.9em'
                }}>No.</th>
              </tr>
            </thead>
            <tbody>
              {sortedEntries.map((entry) => (
                <tr key={entry.id} style={{
                  backgroundColor: entry.id % 2 === 0 ? '#f9f9f9' : '#ffffff',
                  height: `${rowHeight}px`
                }}>
                  <td style={{
                    ...tableCellStyle,
                    padding: '6px',
                    whiteSpace: 'nowrap',
                    fontSize: '0.9em'
                  }}>{entry.date}</td>
                  <td style={{
                    ...tableCellStyle,
                    padding: '6px',
                    fontSize: '0.9em'
                  }}>{entry.name}</td>
                  <td style={{
                    ...tableCellStyle,
                    padding: '6px',
                    fontSize: '0.9em'
                  }}>{entry.route}</td>
                  <td style={{
                    ...tableCellStyle,
                    padding: '6px',
                    textAlign: 'right',
                    whiteSpace: 'nowrap',
                    fontSize: '0.9em'
                  }}>{formatDistance(entry.distance)}</td>
                  <td style={{
                    ...tableCellStyle,
                    padding: '6px',
                    textAlign: 'center',
                    fontSize: '0.9em'
                  }}>{entry.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!isExpenseReportShown && (
          <button 
            onClick={handleShowExpenseReport}
            style={{
              ...buttonStyle,
              backgroundColor: '#2196F3',
              marginTop: '10px'
            }}
          >
            精算書を作成
          </button>
        )}
      </div>
    );
  };

  const parseExpenseData = (text) => {
    setShowExpenseReport(false);
    let entryCounter = 0;

    // 前処理：改行とスペースの正規化
    const normalizedText = text
      .replace(/\r\n/g, '\n')
      .replace(/\n+/g, '\n')
      .trim();

    // 【ピノ】で始まるデータを個別に抽出
    const entries = normalizedText.split('【ピノ】')
      .filter(entry => entry.trim())
      .map(entry => {
        const fullEntry = '【ピノ】' + entry.trim();
        const kmMatch = fullEntry.match(/.*?(\d+\.?\d*)(?:km|㎞|ｋｍ|kｍ)/i);
        if (kmMatch) {
          entryCounter++;
          return {
            id: entryCounter,
            content: fullEntry.substring(0, fullEntry.indexOf(kmMatch[0]) + kmMatch[0].length)
          };
        }
        return null;
      })
      .filter(entry => entry);

    console.log(`抽出されたエントリ数: ${entryCounter}`);

    const expensesByPerson = {};
    const allEntries = [];  // 一覧表示用の配列

    entries.forEach(({id, content: entry}) => {
      const basicInfo = entry.match(/【ピノ】\s*([^　\s]+(?:[ 　]+[^　\s]+)*)\s+(\d+\/\d+)\s*\([月火水木金土日]\)/);
      if (!basicInfo) {
        console.log(`エントリ ${id}: 基本情報が見つかりません:`, entry);
        return;
      }

      const name = basicInfo[1].trim();
      const date = basicInfo[2];

      const distanceMatch = entry.match(/(\d+\.?\d*)(?:km|㎞|ｋｍ|kｍ)/i);
      if (!distanceMatch) {
        console.log(`エントリ ${id}: 距離が見つかりません:`, entry);
        return;
      }

      const distance = parseFloat(distanceMatch[1]);

      const routeStart = entry.indexOf(')') + 1;
      const routeEnd = entry.lastIndexOf(distanceMatch[0]);
      let route = entry.substring(routeStart, routeEnd)
        .replace(/\n/g, '')
        .trim();

      // 一覧表示用のエントリを追加
      allEntries.push({
        id,
        name,
        date,
        route,
        distance
      });

      if (!expensesByPerson[name]) {
        expensesByPerson[name] = {};
      }

      if (!expensesByPerson[name][date]) {
        expensesByPerson[name][date] = {
          details: [],
          totalDistance: 0,
          transportationFee: 0,
          dailyAllowance: DAILY_ALLOWANCE
        };
      }

      expensesByPerson[name][date].details.push({
        route,
        distance
      });
    });

    // 日付ごとの集計と合計の計算
    Object.keys(expensesByPerson).forEach(name => {
      Object.keys(expensesByPerson[name])
        .filter(k => k !== 'summary')
        .forEach(date => {
          const dayData = expensesByPerson[name][date];
          dayData.totalDistance = dayData.details.reduce(
            (sum, detail) => sum + detail.distance,
            0
          );
          dayData.transportationFee = calculateTransportationFee(dayData.totalDistance);
        });

      const dates = Object.keys(expensesByPerson[name]).filter(k => k !== 'summary');
      let totalDistance = 0;
      let totalTransportation = 0;
      let totalDailyAllowance = 0;

      dates.forEach(date => {
        const dayData = expensesByPerson[name][date];
        totalDistance += dayData.totalDistance;
        totalTransportation += dayData.transportationFee;
        totalDailyAllowance += dayData.dailyAllowance;
      });

      expensesByPerson[name].summary = {
        totalDistance,
        totalTransportation,
        totalDailyAllowance,
        grandTotal: totalTransportation + totalDailyAllowance
      };
    });

    // データを保存
    setParsedData({
      entries: allEntries,
      expensesByPerson: expensesByPerson
    });
  };

  const clearData = () => {
    setInputText('');
    setParsedData(null);
    setShowExpenseReport(false);
  };

  // 個別の精算書ダウンロード
  const downloadSingleReport = async (name) => {
    if (!parsedData?.expensesByPerson) return;
    
    try {
      const reportElement = document.getElementById(`report-${name}`);
      if (reportElement) {
        const canvas = await html2canvas(reportElement, {
          scale: 2,  // 高解像度
          backgroundColor: '#ffffff',
          logging: false,  // デバッグログを無効化
          useCORS: true   // クロスオリジン対応
        });
        
        const link = document.createElement('a');
        link.download = `精算書_${name}_${calculationDate}.png`;
        link.href = canvas.toDataURL('image/png', 1.0);  // 最高品質でエクスポート
        link.click();
      }
    } catch (error) {
      console.error('精算書のダウンロードに失敗しました:', error);
    }
  };

  // 全担当者の精算書を順番にダウンロード
  const downloadAllPersonsReports = async () => {
    if (!parsedData?.expensesByPerson) return;
    
    try {
      // すべての担当者の精算書を処理
      for (const name of Object.keys(parsedData.expensesByPerson)) {
        // 一時的に担当者を選択して表示
        setSelectedPerson(name);
        
        // DOMの更新を待つ
        await new Promise(resolve => setTimeout(resolve, 100));

        // 個別にダウンロード
        await downloadSingleReport(name);

        // ダウンロード間隔を設定
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    } catch (error) {
      console.error('精算書のダウンロードに失敗しました:', error);
    }
  };

  // 金額フォーマット関数を追加
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ja-JP').format(amount);
  };

  // 精算書表示時に最初の担当者を自動選択
  const handleShowExpenseReport = () => {
    setShowExpenseReport(true);
    // 最初の担当者を自動選択
    if (parsedData?.expensesByPerson) {
      const firstPerson = Object.keys(parsedData.expensesByPerson)[0];
      setSelectedPerson(firstPerson);
    }
  };

  // 精算書コンポーネント
  const ExpenseReport = ({ name, data }) => {
    return (
      <div 
        id={`report-${name}`} 
        style={{ 
          backgroundColor: '#ffffff', 
          padding: '15px',
          display: selectedPerson === name ? 'block' : 'none',
          fontSize: '0.9em'
        }}
      >
        <h3 style={{ 
          fontSize: '1.2em',
          marginBottom: '15px'
        }}>{name}様 1月 社内通貨（交通費）清算額</h3>

        <table style={{ 
          width: '100%', 
          borderCollapse: 'collapse',
          marginBottom: '15px'
        }}>
          <thead>
            <tr>
              <th style={{
                ...tableHeaderStyle,
                padding: '6px',
                fontSize: '0.95em',  // ヘッダーのフォントサイズ
                backgroundColor: '#f5f5f5'
              }}>日付</th>
              <th style={{
                ...tableHeaderStyle,
                padding: '6px',
                fontSize: '0.95em',
                backgroundColor: '#f5f5f5'
              }}>経路</th>
              <th style={{
                ...tableHeaderStyle,
                padding: '6px',
                fontSize: '0.95em',
                backgroundColor: '#f5f5f5'
              }}>距離(km)</th>
              <th style={{
                ...tableHeaderStyle,
                padding: '6px',
                fontSize: '0.95em',
                backgroundColor: '#f5f5f5'
              }}>交通費</th>
              <th style={{
                ...tableHeaderStyle,
                padding: '6px',
                fontSize: '0.95em',
                backgroundColor: '#f5f5f5'
              }}>運転手当</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data)
              .filter(([key]) => key !== 'summary')
              .map(([date, dayData]) => (
                <tr key={date}>
                  <td style={tableCellStyle}>{date}</td>
                  <td style={tableCellStyle}>
                    {dayData.details.map((d, i) => (
                      <div key={i}>{d.route}</div>
                    ))}
                  </td>
                  <td style={{...tableCellStyle, textAlign: 'right'}}>
                    {formatDistance(dayData.totalDistance)}
                  </td>
                  <td style={{...tableCellStyle, textAlign: 'right'}}>
                    {formatCurrency(dayData.transportationFee)}
                  </td>
                  <td style={{...tableCellStyle, textAlign: 'right'}}>
                    {formatCurrency(dayData.dailyAllowance)}
                  </td>
                </tr>
              ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan="5" style={{
                ...tableCellStyle,
                padding: '6px',
                textAlign: 'right',
                borderTop: '2px solid #000',
                fontSize: '0.95em'
              }}>
                合計金額: {formatCurrency(data.summary.grandTotal)}円
              </td>
            </tr>
          </tfoot>
        </table>

        <div style={{ 
          marginTop: '15px', 
          borderTop: '1px solid #ccc', 
          paddingTop: '8px',
          fontSize: '0.85em',
          color: '#666'
        }}>
          計算日時: {calculationDate}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>PINO精算アプリケーション</h1>
      
      {/* 入力フォーム */}
      <div style={{ 
        marginBottom: '20px',
        transition: 'height 0.3s ease-in-out'  // スムーズな高さ変更
      }}>
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          style={{ 
            width: '100%', 
            height: parsedData ? '100px' : '200px',  // データ解析後は高さを半分に
            marginBottom: '10px',
            transition: 'height 0.3s ease-in-out',
            resize: 'none'  // 手動リサイズを無効化
          }}
          placeholder="精算データを貼り付けてください"
        />
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={() => parseExpenseData(inputText)} 
            style={buttonStyle}
          >
            データを解析
          </button>
          <button 
            onClick={clearData} 
            style={{...buttonStyle, backgroundColor: '#f44336'}}
          >
            クリア
          </button>
        </div>
      </div>

      {/* データ一覧表示 */}
      {parsedData?.entries && (
        <EntryList 
          entries={parsedData.entries} 
          isExpenseReportShown={showExpenseReport} 
        />
      )}

      {/* 精算書表示部分 */}
      {showExpenseReport && parsedData?.expensesByPerson && (
        <div style={{ marginTop: '30px', borderTop: '2px solid #ccc', paddingTop: '15px' }}>
          <h2 style={{ fontSize: '1.3em' }}>精算書</h2>
          
          {/* 担当者タブ */}
          <div style={{ 
            display: 'flex', 
            gap: '8px', 
            marginBottom: '15px',
            flexWrap: 'wrap'
          }}>
            {Object.keys(parsedData.expensesByPerson).map(name => (
              <button
                key={name}
                onClick={() => setSelectedPerson(name)}
                style={{
                  ...buttonStyle,
                  backgroundColor: selectedPerson === name ? '#2196F3' : '#808080',
                  padding: '5px 10px',
                  fontSize: '0.85em'
                }}
              >
                {name}
              </button>
            ))}
          </div>

          {/* 精算書表示 */}
          {Object.entries(parsedData.expensesByPerson).map(([name, data]) => (
            <ExpenseReport key={name} name={name} data={data} />
          ))}

          {/* ダウンロードボタン */}
          <div style={{
            marginTop: '30px',
            borderTop: '2px solid #ccc',
            paddingTop: '20px',
            display: 'flex',
            justifyContent: 'center',
            gap: '20px'
          }}>
            <button
              onClick={() => downloadSingleReport(selectedPerson)}
              style={{
                ...buttonStyle,
                backgroundColor: '#2196F3',
                fontSize: '0.9em',
                padding: '10px 20px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
              }}
            >
              表示中の精算書をダウンロード
            </button>
            <button
              onClick={downloadAllPersonsReports}
              style={{
                ...buttonStyle,
                backgroundColor: '#9c27b0',
                fontSize: '0.9em',
                padding: '10px 20px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
              }}
            >
              全担当者の精算書をダウンロード
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const tableHeaderStyle = {
  border: '1px solid #ddd',
  padding: '8px',
  backgroundColor: '#f2f2f2',
  textAlign: 'left'
};

const tableCellStyle = {
  border: '1px solid #ddd',
  padding: '8px'
};

const buttonStyle = {
  padding: '8px 16px',
  backgroundColor: '#4CAF50',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer'
};

export default App; 