// App.js
import React, { useState } from 'react';
import './App.css';


function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [prediction, setPrediction] = useState('');
  const [likelihood, setLikelihood] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const [error, setError] = useState('');

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setPrediction('');
    setLikelihood(null);
    setError('');
    setImageUrl('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedFile) {
      setError('Please upload an image file');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('http://localhost:5000/predict', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Something went wrong!');
      }

      const data = await response.json();
      setPrediction(data.predicted_class);
      setLikelihood(data.likelihood);
      setImageUrl(URL.createObjectURL(selectedFile));
    } catch (error) {
      setError(error.message);
    }
  };

  return (
    <div className="container-fluid app-wrapper">
      <div className="row">
        {/* Left Section */}
        <div className="col-lg-6 left-section">
          <div className="branding">
            {/* <div className="logo">LOGO</div> */}
            <h1 id="custom-heading">SKIN<br></br> DISEASE</h1>
            <div className="detector-box">DETECTOR</div>
            <p className="subtitle">Instant Skin Health<br></br> Checkup: Upload & Get<br></br> Results</p>
            <p className="note text-danger">Note: This result is AI-generated and not a <br></br>substitute for professional medical advice.<br></br> For further details and personalized treatment<br></br> options, consult your healthcare provider.</p>
          </div>
        </div>

        {/* Right Section */}
        <div className="col-lg-6 right-section">
          <div className="predictions">
            <h2>Prediction:{prediction}</h2>
            <p className="likelihood text-success">Likelihood: {likelihood !== null ? Math.round(likelihood * 100) : 0}%</p>
          </div>

          <div className="upload-section">
              <form onSubmit={handleSubmit} className="upload-form">
                    <div>
                      <input
                        type="file"
                        onChange={handleFileChange}
                        accept=".png,.jpg,.jpeg"
                        required
                        id="file-upload"
                        style={{ display: 'none' }} // Hide the input
                      />
                      <button 
                        type="button"
                        onClick={() => document.getElementById('file-upload').click()} 
                        className="btn btn-secondary upload-btn"
                        >
                        Upload Image
                      </button>
                      <button 
                  type="submit"
                  className="btn bg-CoconutBrown predict-btn"
                >
                  Predict
                </button>
                  </div>
              </form>
          </div>

          {imageUrl && <img src={imageUrl} alt="Uploaded skin" className="uploaded-image" />}
          {error && (
            <div className="error-message">
              <h2>Error: {error}</h2>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

export default App;