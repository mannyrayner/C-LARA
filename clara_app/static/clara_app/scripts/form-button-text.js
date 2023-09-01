//console.log("Script loaded");

//document.getElementById('create-segmented-text-form').onsubmit = function() {
//  document.getElementById('submit-button').textContent = "Processing...";
//};

// Function to update button text based on selected option
function updateButton() {
  var selectedValue;
  var radioButtons = document.getElementsByName('text_choice');
  
  // Get the selected value
  for(var i = 0; i < radioButtons.length; i++){
	if(radioButtons[i].checked){
	  selectedValue = radioButtons[i].value;
	  break;
	}
  }

  var buttonText;
  switch(selectedValue) {
	case 'generate':
	  buttonText = 'Create';
	  break;
	case 'improve':
	  buttonText = 'Improve';
	  break;
	case 'manual':
	  buttonText = 'Save';
	  break;
	case 'load_archived':
	  buttonText = 'Load';
	  break;
	case 'correct':
	  buttonText = 'Correct';
	  break;
	case 'jieba':
	  buttonText = 'Use Jieba';
	  break;
	default:
	  buttonText = 'Submit';
  }
  document.getElementById('submit-button').textContent = buttonText;
}

// Update button when the selection changes
var radioButtons = document.getElementsByName('text_choice');
for(var i = 0; i < radioButtons.length; i++){
  radioButtons[i].addEventListener('change', updateButton);
}

// Set initial button text
window.onload = updateButton;