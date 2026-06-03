import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';

type PagesFunction = (context: { request: Request }) => Promise<Response>;

function downloadName(name: string) {
  const clean = (name || 'amazon-labels.pdf').replace(/\.pdf$/i, '').replace(/[^\w.-]+/g, '-').replace(/^-+|-+$/g, '') || 'amazon-labels';
  return `${clean}-made-in-china.pdf`;
}

async function addTextTo27UpPdf(input: ArrayBuffer, labelText: string) {
  const pdf = await PDFDocument.load(input);
  const font = await pdf.embedFont(StandardFonts.Helvetica);

  for (const page of pdf.getPages()) {
    const { width, height } = page.getSize();
    const cols = 3;
    const rows = 9;
    const marginX = width * 0.055;
    const marginY = height * 0.035;
    const usableWidth = width - marginX * 2;
    const usableHeight = height - marginY * 2;
    const cellWidth = usableWidth / cols;
    const cellHeight = usableHeight / rows;
    const fontSize = Math.max(6, Math.min(9, cellHeight * 0.16));

    for (let row = 0; row < rows; row += 1) {
      for (let col = 0; col < cols; col += 1) {
        page.drawText(labelText, {
          x: marginX + col * cellWidth + cellWidth * 0.06,
          y: height - marginY - (row + 1) * cellHeight + cellHeight * 0.12,
          size: fontSize,
          font,
          color: rgb(0, 0, 0),
        });
      }
    }
  }

  return pdf.save();
}

export const onRequestPost: PagesFunction = async ({ request }) => {
  const form = await request.formData();
  const file = form.get('file');
  const labelText = String(form.get('label_text') || 'Made in China').trim().slice(0, 80) || 'Made in China';

  if (!(file instanceof File)) {
    return Response.json({ detail: '请上传 PDF 文件。' }, { status: 400 });
  }
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    return Response.json({ detail: '请上传 PDF 文件。' }, { status: 400 });
  }

  try {
    const output = await addTextTo27UpPdf(await file.arrayBuffer(), labelText);
    const filename = downloadName(file.name);
    return new Response(output, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    return Response.json({ detail: `PDF 处理失败：${error instanceof Error ? error.message : '未知错误'}` }, { status: 400 });
  }
};
