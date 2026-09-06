import { isOtherHand, trialBanner, type TrialInfo } from '../hooks/useTrial';

type TrialBannerProps = {
  trial: TrialInfo;
  /** The name of the image the subject draws on, for the hand warning. */
  imageName: string | null;
};

/** The trial the console scores, at the top of the mark page. */
export function TrialBanner({ trial, imageName }: TrialBannerProps) {
  const { text, tone } = trialBanner(trial);
  const answered =
    trial.manual !== true && trial.can_draw === true && trial.felt_answered === true;

  return (
    <div className={`trial-banner trial-banner-${tone}`} role="status">
      <span className="trial-banner-text">{text}</span>
      {answered && (
        <span className="trial-banner-answered">Answered, you can send again</span>
      )}
      {isOtherHand(trial, imageName) && (
        <span className="trial-banner-wrong-hand"> · the image is the other hand</span>
      )}
    </div>
  );
}
