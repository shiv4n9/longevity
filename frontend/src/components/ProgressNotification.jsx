import React from 'react'

function ProgressNotification({ message }) {
  return (
    <div className="progress-notification">
      <div className="spinner"></div>
      <span>{message}</span>
    </div>
  )
}

export default ProgressNotification
