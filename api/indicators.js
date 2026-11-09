import {collect,selectSeries} from '../lib/provider.mjs';
export default async function handler(req,res) {
 if(req.method!=='GET'){res.setHeader('Allow','GET'); return res.status(405).json({error:'GET 요청만 지원합니다.'});}
 const id=typeof req.query?.id==='string'?req.query.id:'';
 try{selectSeries(id);}catch{return res.status(400).json({error:'등록된 지표 ID가 필요합니다.'});}
 try {
  const result=await collect(id);
  res.setHeader('Cache-Control','public, s-maxage=900');
  return res.status(200).json(result);
 }catch {
  res.setHeader('Cache-Control','no-store');
  return res.status(503).json({error:'공식 통계 수집에 실패했습니다. 잠시 후 다시 시도하세요. 임의 수치는 표시하지 않습니다.'});
 }
}
