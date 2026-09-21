import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../test/utils';
import { successResponse } from '../test/fixtures';
import { gradeAnswer, REAL_SAMPLES, sampleDate } from '../data/realSample';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, analyzeRaster: vi.fn(), getSession: vi.fn(), inspectRaster: vi.fn() };
});

import { analyzeRaster, inspectRaster } from '../services/api';
import { useSatQuery } from '../context/SatQueryContext';
import { DemoScenarioBar } from './DemoScenarioBar';
import { QueryInput } from './QueryInput';
import { ImageUploader } from './ImageUploader';
import { ReferenceCheck } from './ReferenceCheck';

const TIFF_BYTES = new Uint8Array([0x49, 0x49, 0x2a, 0x00, ...new Array(512).fill(3)]);
const FIRST = REAL_SAMPLES[0];
const SECOND = REAL_SAMPLES[1];
const MCQ = FIRST.questions.find((q) => q.type === 'mcq')!;
const BINARY = FIRST.questions.find((q) => q.type === 'binary')!;

/** The studio's preset bar, uploader and query box, the context state they drive, and a start button. */
function Probe() {
  const { image1, query, activeRealSample, results, resultSource, analysisError, startAnalysis } = useSatQuery();
  return (
    <>
      <DemoScenarioBar />
      <ImageUploader />
      <QueryInput />
      <button onClick={() => startAnalysis()}>start</button>
      <output data-testid="image">{image1?.name ?? ''}</output>
      <output data-testid="crs">{image1?.crs ?? 'none'}</output>
      <output data-testid="status">{image1?.metadataStatus ?? ''}</output>
      <output data-testid="preview">{image1?.previewUrl ?? ''}</output>
      <output data-testid="query">{query}</output>
      <output data-testid="active">{activeRealSample?.id ?? 'none'}</output>
      <output data-testid="source">{resultSource ?? ''}</output>
      <output data-testid="answer">{results?.answerText ?? ''}</output>
      <output data-testid="error">{analysisError ?? ''}</output>
    </>
  );
}

const cardName = (s: (typeof REAL_SAMPLES)[number]) => `Live model: ${s.country}, ${sampleDate(s)}`;

/** Loads a live-model preset, then picks one of its questions from the query box. */
function pick(sample: (typeof REAL_SAMPLES)[number], question: string) {
  fireEvent.click(screen.getByRole('button', { name: cardName(sample) }));
  fireEvent.click(screen.getByRole('button', { name: question }));
}

/** Picks a file in Image 1's hidden file input, as the browser's file dialog would. */
function upload(container: HTMLElement, file: File) {
  const input = container.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files: [file] } });
}

beforeEach(() => {
  vi.mocked(analyzeRaster).mockReset();
  vi.mocked(inspectRaster).mockReset();
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, blob: async () => new Blob([TIFF_BYTES]) })));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('live model presets in the studio', () => {
  it('offers one card per real image', () => {
    renderWithProviders(<Probe />);
    for (const s of REAL_SAMPLES) {
      expect(screen.getByRole('button', { name: cardName(s) })).toBeInTheDocument();
    }
  });

  it('offers each image its own questions, and only while it is loaded', () => {
    renderWithProviders(<Probe />);
    expect(screen.queryByRole('button', { name: MCQ.question })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: cardName(FIRST) }));
    for (const q of FIRST.questions) {
      expect(screen.getByRole('button', { name: q.question })).toBeInTheDocument();
    }
    expect(screen.getByText(new RegExp(`tile ${FIRST.tile} was\\s+never seen in training`))).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: cardName(SECOND) }));
    expect(screen.getByTestId('active')).toHaveTextContent(SECOND.id);
    expect(screen.getByTestId('image')).toHaveTextContent(SECOND.rasterFile);
    for (const q of SECOND.questions) {
      expect(screen.getByRole('button', { name: q.question })).toBeInTheDocument();
    }

    // A demo scenario puts the ISRO queries back.
    fireEvent.click(screen.getByText('Single Scene Understanding'));
    expect(screen.queryByRole('button', { name: SECOND.questions[0].question })).toBeNull();
    expect(screen.getByTestId('active')).toHaveTextContent('none');
  });

  it('loads the real image and the chosen question', () => {
    renderWithProviders(<Probe />);
    pick(FIRST, MCQ.question);

    expect(screen.getByTestId('image')).toHaveTextContent(FIRST.rasterFile);
    expect(screen.getByTestId('query')).toHaveTextContent(MCQ.question);
    expect(screen.getByTestId('active')).toHaveTextContent(FIRST.id);
  });

  it('uploads the real GeoTIFF, not a rasterized preview', async () => {
    vi.mocked(analyzeRaster).mockResolvedValue(successResponse);
    renderWithProviders(<Probe />);
    pick(FIRST, BINARY.question);
    fireEvent.click(screen.getByText('start'));

    await waitFor(() => expect(analyzeRaster).toHaveBeenCalled(), { timeout: 5000 });
    const [query, files] = vi.mocked(analyzeRaster).mock.calls[0];
    expect(query).toBe(BINARY.question);
    expect((files as File[]).map((f) => f.name)).toEqual([FIRST.rasterFile]);
    expect(fetch).toHaveBeenCalledWith(`/real/${FIRST.rasterFile}`);
  });

  it('shows an error instead of a demo answer when the model server is down', async () => {
    vi.mocked(analyzeRaster).mockRejectedValue(
      new Error('API error (503): {"detail":"Model server at http://127.0.0.1:8001 is not reachable (ConnectError)."}'),
    );
    renderWithProviders(<Probe />);
    pick(FIRST, BINARY.question);
    fireEvent.click(screen.getByText('start'));

    await waitFor(() => expect(screen.getByTestId('error')).toHaveTextContent('model server is not running'), {
      timeout: 5000,
    });
    expect(screen.getByTestId('error')).toHaveTextContent('127.0.0.1:8001 is not reachable');
    expect(screen.getByTestId('answer')).toHaveTextContent('');
    expect(screen.getByTestId('source')).toHaveTextContent('');
  });
});

describe('uploading a sample by hand', () => {
  it('treats an uploaded sample GeoTIFF as that sample and sends its own bytes', async () => {
    vi.mocked(analyzeRaster).mockResolvedValue(successResponse);
    const { container } = renderWithProviders(<Probe />);
    const file = new File([TIFF_BYTES], SECOND.rasterFile, { type: 'image/tiff' });
    upload(container, file);

    expect(screen.getByTestId('active')).toHaveTextContent(SECOND.id);
    expect(screen.getByTestId('crs')).toHaveTextContent(SECOND.crs);
    expect(screen.getByTestId('preview')).toHaveTextContent(`/real/${SECOND.previewFile}`);
    expect(inspectRaster).not.toHaveBeenCalled(); // its facts are already known

    const question = SECOND.questions[0].question;
    fireEvent.click(screen.getByRole('button', { name: question }));
    fireEvent.click(screen.getByText('start'));
    await waitFor(() => expect(analyzeRaster).toHaveBeenCalled(), { timeout: 5000 });
    expect(vi.mocked(analyzeRaster).mock.calls[0][1]).toEqual([file]);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('accepts the PNG too, without inventing a georeference for it', () => {
    const { container } = renderWithProviders(<Probe />);
    upload(container, new File([new Uint8Array([137, 80, 78, 71])], FIRST.previewFile, { type: 'image/png' }));

    expect(screen.getByTestId('active')).toHaveTextContent(FIRST.id);
    expect(screen.getByTestId('image')).toHaveTextContent(FIRST.previewFile);
    expect(screen.getByTestId('crs')).toHaveTextContent('none');
  });
});

describe('any other upload', () => {
  it('shows nothing invented while reading, then what the backend read from the file', async () => {
    let resolve: (v: Awaited<ReturnType<typeof inspectRaster>>) => void = () => {};
    vi.mocked(inspectRaster).mockReturnValue(new Promise((r) => (resolve = r)));
    const { container } = renderWithProviders(<Probe />);
    upload(container, new File([TIFF_BYTES], 'my_scene.tif', { type: 'image/tiff' }));

    // The old uploader showed EPSG:32643 and 0.65 m for any TIFF.
    expect(screen.getByTestId('status')).toHaveTextContent('reading');
    expect(screen.getByTestId('crs')).toHaveTextContent('none');
    expect(screen.getByTestId('active')).toHaveTextContent('none');

    resolve({
      metadata: {
        ...FIRST_AS_METADATA,
        imageId: 'img_1_upload',
        name: 'upload.tif',
        crs: 'EPSG:32644',
        gsdMeters: 5.8,
      },
      previewDataUrl: 'data:image/png;base64,AAAA',
    });
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('read'));
    expect(screen.getByTestId('crs')).toHaveTextContent('EPSG:32644');
    expect(screen.getByTestId('image')).toHaveTextContent('my_scene.tif'); // the user's own file name
    expect(screen.getByTestId('preview')).toHaveTextContent('data:image/png;base64,AAAA');
  });

  it('never uploads a removed image', async () => {
    vi.mocked(inspectRaster).mockReturnValue(new Promise(() => {}));
    vi.mocked(analyzeRaster).mockResolvedValue(successResponse);
    const { container } = renderWithProviders(<Probe />);
    upload(container, new File([TIFF_BYTES], 'my_scene.tif', { type: 'image/tiff' }));
    fireEvent.click(screen.getByTitle('Remove image'));
    fireEvent.click(screen.getByText('start'));

    await waitFor(() => expect(analyzeRaster).toHaveBeenCalled(), { timeout: 5000 });
    expect(vi.mocked(analyzeRaster).mock.calls[0][1]).toEqual([]);
  });

  it('leaves the facts unknown when the backend cannot be asked', async () => {
    vi.mocked(inspectRaster).mockRejectedValue(new Error('Failed to fetch'));
    const { container } = renderWithProviders(<Probe />);
    upload(container, new File([TIFF_BYTES], 'my_scene.tif', { type: 'image/tiff' }));

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unavailable'));
    expect(screen.getByTestId('crs')).toHaveTextContent('none');
  });
});

const FIRST_AS_METADATA = {
  imageId: 'x',
  name: 'x',
  format: 'geotiff' as const,
  crs: null,
  bandCount: 3,
  detectedModality: 'optical' as const,
  gsdMeters: null,
  acquisitionTimestamp: null,
  nodataPercent: 0,
  cloudMaskPercent: null,
  previewUrl: '',
};

describe('grading against the BigEarthNet reference', () => {
  it('reads yes/no and option-letter answers from the answer text', () => {
    const binary = gradeAnswer(FIRST, BINARY.question, `${BINARY.answer === 'no' ? 'No' : 'Yes'} (model probability 78%)`);
    expect(binary).toMatchObject({ reference: BINARY.answer, correct: true });

    const right = gradeAnswer(FIRST, MCQ.question, `${MCQ.answer}) something (model probability 34%)`);
    expect(right?.correct).toBe(true);
    expect(right?.referenceText.startsWith(`${MCQ.answer}) `)).toBe(true);

    const wrongLetter = MCQ.answer === 'a' ? 'b' : 'a';
    expect(gradeAnswer(FIRST, MCQ.question, `${wrongLetter}) other`)?.correct).toBe(false);
  });

  it('reports an unreadable reply and ignores questions it has no reference for', () => {
    expect(gradeAnswer(FIRST, BINARY.question, 'The image shows farmland.')).toMatchObject({ modelAnswer: null, correct: false });
    expect(gradeAnswer(FIRST, 'Is this a port?', 'No')).toBeNull();
    // Another sample's question has no reference on this one.
    expect(gradeAnswer(FIRST, SECOND.questions[0].question, 'No')).toBeNull();
  });

  it('renders the verdict beside the reference', () => {
    render(<ReferenceCheck sample={FIRST} query={MCQ.question} answerText={`${MCQ.answer}) x`} />);
    expect(screen.getByTestId('reference-check')).toHaveTextContent('the model matches it');
  });
});
