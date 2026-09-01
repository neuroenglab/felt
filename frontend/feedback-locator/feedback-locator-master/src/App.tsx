import React, { useState } from "react";
import { FeedbackLocator, SensationLocation } from "./FeedbackLocator";
import { BodyPartSelector, SelectionResult } from "./BodyPartSelector";


const myAssets = import.meta.glob('../assets/*.svg', { 
    eager: true, 
    query: '?url', 
    import: 'default' 
  }) as Record<string, string>;

console.log(myAssets);

export const App: React.FC = () => {
    const [selection, setSelection] = useState<SelectionResult | null>(null);
    const [feedbackLocation, setFeedbackLocation] = useState<SensationLocation | undefined>(undefined);

    const handleSelectionUpdate = (newSelection: SelectionResult) => {
        setSelection(newSelection);
        // Reset feedback when the body part changes to avoid coordinate mismatch
        setFeedbackLocation(undefined);
    };

    return (
        <div style={{ padding: "1.5rem", maxWidth: "800px", margin: "0 auto" }}>
            <h1>Stimulation Feedback Locator</h1>
            
            <BodyPartSelector 
                assets={myAssets}
                onSelect={handleSelectionUpdate} 
                selectedPath={selection?.path} 
            />

            {selection ? (
                <FeedbackLocator
                    imageSrc={selection.path}
                    feedbackLocation={feedbackLocation}
                    onUpdate={setFeedbackLocation}
                    coarseness={90}
                />
            ) : (
                <div style={{ padding: '2rem', textAlign: 'center', background: '#f9f9f9' }}>
                    Please select a body part above to begin.
                </div>
            )}

            <div style={{ marginTop: "1.5rem" }}>
                <h3>Output Data</h3>
                <pre style={{ backgroundColor: "#222", color: "#0f0", padding: "1rem", borderRadius: 4, fontSize: 11 }}>
                    {JSON.stringify({ selection, feedbackLocation }, null, 2)}
                </pre>
            </div>
        </div>
    );
};
